"""Video transport, retained-view coverage and conservative comparison fallbacks."""
from pathlib import Path
from types import SimpleNamespace
import subprocess

import cv2
import numpy as np
import pytest

from fieldwork import video
from fieldwork.spec import Box, Item, Capture, ConditionRecord, Claim, Lane, Severity
from fieldwork.take.frames import Frame, evidence_candidates, select_frames
from fieldwork.take.record import Draft, ViewCoverage, coverage_report
from fieldwork.unbox import align as alignment, pipeline, gate, diff


def test_candidate_pool_preserves_baseline_and_early_view():
    frames=[Frame(f'f{i}',Path(f'{i}.jpg'),i*.25,1. if i<16 else float(i+100),120.) for i in range(48)]
    base=select_frames(frames,k=8);chosen=evidence_candidates(frames,k=8)
    assert {f.frame_id for f in base}<={f.frame_id for f in chosen}
    assert any(f.t<1.5 for f in chosen)
    assert len(chosen)<=16


def test_coverage_requires_retained_evidence_and_never_infers_label():
    draft=Draft(item=Item(type='shirt',brand='Printed brand'),claims=[],code_read=None,listing_text_en='Shirt',
        coverage=[ViewCoverage(region='front',status='shown',evidence=[Box(frame_id='f1',box_2d=[0,0,1000,1000])]),
                  ViewCoverage(region='back',status='shown',evidence=[Box(frame_id='missing',box_2d=[0,0,1000,1000])])])
    report=coverage_report(draft,{'f1'})
    assert [v['status'] for v in report['views']]==['shown','unclear','unclear']
    assert report['needs_more_evidence']
    assert report['guidance'][:2]==['Add a clear back view.', 'Add a clear close-up of the label.']
    assert report['detail_requests']  # overview coverage is not detail coverage


@pytest.fixture
def clip(tmp_path):
    import imageio_ffmpeg
    path=tmp_path/'phone.mp4'
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-nostdin','-loglevel','error',
        '-f','lavfi','-i','testsrc=size=320x240:rate=24','-f','lavfi','-i','sine=frequency=440:sample_rate=44100',
        '-t','1','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',str(path)],check=True,capture_output=True)
    return path


def test_proxy_preserves_original_duration_audio_and_decodes(clip,monkeypatch,tmp_path):
    import imageio_ffmpeg
    original=clip.read_bytes();monkeypatch.setattr(video,'INLINE_LIMIT',len(original)-1)
    # Force conversion using an otherwise valid MOV filename, then allow normal output size.
    clip=clip.rename(clip.with_suffix('.mov'));monkeypatch.setattr(video,'INLINE_LIMIT',20*1024*1024)
    data,mime=video.inline_video(clip);out=tmp_path/'proxy.mp4';out.write_bytes(data)
    assert clip.read_bytes()==original and mime=='video/mp4'
    assert abs(video.validate_video(out)-1.)<.1
    result=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-i',str(out),'-map','0:a:0','-t','0','-f','null','-'],capture_output=True)
    assert result.returncode==0  # an audio stream really survived
    cap=cv2.VideoCapture(str(out));assert cap.read()[0];cap.release()


def test_invalid_video_gives_actionable_error(tmp_path):
    path=tmp_path/'bad.mp4';path.write_bytes(b'not a video')
    with pytest.raises(video.VideoInputError,match='Could not read'):
        video.inline_video(path)


def test_source_size_rejected_before_decode(clip,monkeypatch):
    monkeypatch.setattr(video,'SOURCE_LIMIT',1)
    with pytest.raises(video.VideoInputError,match='128 MiB'):
        video.validate_video(clip)


def test_sift_is_used_only_after_akaze_fails(monkeypatch):
    calls=[]
    def attempt(ref,img,method):
        calls.append(method)
        return alignment.AlignResult(method=='sift',None,30,.8,Path('aligned.jpg') if method=='sift' else None,method)
    monkeypatch.setattr(alignment,'_align_method',attempt)
    assert alignment.align('ref','received').method=='sift'
    assert calls==['akaze','sift']


def test_pairing_keeps_bounded_plausible_candidates(monkeypatch):
    values=iter([np.array([[1.,0.]]),np.array([[.9,0.],[.8,0.],[.7,0.],[.65,0.],[.1,0.]])])
    monkeypatch.setattr(pipeline,'embed',lambda paths:next(values))
    assert pipeline.pair_frames({'f1':Path('ref')},[Path(str(i)) for i in range(5)])==[
        ('f1',Path('0')),('f1',Path('1')),('f1',Path('2'))]


def test_gate_recovers_second_candidate_without_double_counting(tmp_path,monkeypatch):
    record=ConditionRecord(id='item',item=Item(type='shirt'),claims=[],
        capture=Capture(code_expected='',code_seen=False,take_sha256='hash',frames=['f1']))
    monkeypatch.setattr(gate,'_near_identical',lambda *a:False)
    def align(ref,received):
        return SimpleNamespace(ok=received.name=='second',warped_path=tmp_path/'warp.jpg' if received.name=='second' else None)
    monkeypatch.setattr(gate,'align',align);monkeypatch.setattr(gate,'change_regions',lambda *a,**k:[])
    result=gate.check(record,{'f1':Path('ref')},[('f1',Path('first')),('f1',Path('second'))],tmp_path/'work')
    assert result.pairs_total==1 and result.pairs_aligned==1
    assert not result.limitations and result.verdict=='consistent'


def test_no_comparable_area_is_not_no_change(tmp_path,monkeypatch):
    image=np.full((100,100,3),100,np.uint8);path=tmp_path/'image.jpg';cv2.imwrite(str(path),image)
    with pytest.raises(diff.InsufficientComparisonArea):
        diff.change_regions(path,path,valid_mask=np.zeros((100,100),np.uint8),method='colour')
    record=ConditionRecord(id='item',item=Item(type='shirt'),claims=[],
        capture=Capture(code_expected='',code_seen=False,take_sha256='hash',frames=['f1']))
    monkeypatch.setattr(gate,'_near_identical',lambda *a:False)
    monkeypatch.setattr(gate,'align',lambda *a:SimpleNamespace(ok=True,warped_path=path))
    def unavailable(*a,**k):raise diff.InsufficientComparisonArea()
    monkeypatch.setattr(gate,'change_regions',unavailable)
    result=gate.check(record,{'f1':path},[('f1',path)],tmp_path/'work')
    assert result.verdict=='cant_tell' and result.limitations


def test_flaw_outside_overlap_is_uncheckable_not_missing(tmp_path,monkeypatch):
    mask=np.zeros((100,100),np.uint8);mask[:,30:]=255
    path=tmp_path/'valid.png';cv2.imwrite(str(path),mask)
    record=ConditionRecord(id='item',item=Item(type='shirt'),
        claims=[Claim(id='c1',lane=Lane.shown,code='hole',severity=Severity.minor,
                      evidence=[Box(frame_id='f1',box_2d=[100,0,300,200])])],
        capture=Capture(code_expected='',code_seen=False,take_sha256='hash',frames=['f1']))
    monkeypatch.setattr(gate,'_near_identical',lambda *a:False)
    monkeypatch.setattr(gate,'align',lambda *a:SimpleNamespace(ok=True,warped_path=Path('warp'),valid_mask_path=path))
    monkeypatch.setattr(gate,'change_regions',lambda *a,**k:[])
    monkeypatch.setattr(gate.judge,'flaw_still_there',lambda *a:pytest.fail('Unobserved flaw must not be judged missing'))
    result=gate.check(record,{'f1':Path('ref')},[('f1',Path('received'))],tmp_path/'work')
    assert result.verdict=='cant_tell' and not result.findings


def test_invalid_upload_returns_actionable_api_error(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from fieldwork import api
    from fieldwork.take import pipeline as take_pipeline
    from fieldwork.store import LocalStore
    isolated = LocalStore(tmp_path/'store')
    monkeypatch.setattr(api, 'store', isolated)
    monkeypatch.setattr(take_pipeline, 'store', isolated)
    response=TestClient(api.app).post('/take',files={'video':('bad.mp4',b'not video','video/mp4')})
    assert response.status_code==422 and 'Could not read' in response.json()['detail']


def test_fallback_alignment_alone_cannot_suggest_consistent(tmp_path,monkeypatch):
    record=ConditionRecord(id='item',item=Item(type='shirt'),claims=[],
        capture=Capture(code_expected='',code_seen=False,take_sha256='hash',frames=['f1']))
    monkeypatch.setattr(gate,'_near_identical',lambda *a:False)
    monkeypatch.setattr(gate,'align',lambda *a:SimpleNamespace(ok=True,warped_path=Path('warp'),method='sift'))
    monkeypatch.setattr(gate,'change_regions',lambda *a,**k:[])
    result=gate.check(record,{'f1':Path('ref')},[('f1',Path('received'))],tmp_path/'work')
    assert result.verdict=='cant_tell'
    assert any('provisional' in note for note in result.limitations)
