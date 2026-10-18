"""Untrusted outlines, mixed-media evidence and background-only correspondence."""
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from fieldwork.regions import valid_outline, reference_masks
from fieldwork.spec import Box, Capture, ConditionRecord, Item
from fieldwork.take import pipeline
from fieldwork.take.record import Draft, ViewCoverage, coverage_report
from fieldwork.unbox import gate
from fieldwork.unbox.align import align

OUTLINE=[[100,100],[100,500],[100,900],[900,900],[900,500],[900,100]]


@pytest.mark.parametrize('outline',[[],[[0,0]]*6,[[0,0],[0,1001],[200,900],[400,800],[900,500],[800,100]],
    [[0,0],[0,900],[400,900],[900,900],[900,0],[True,0]]])
def test_invalid_outlines_are_rejected(outline):
    assert not valid_outline(outline)


def test_outline_not_transplanted_to_other_cited_frame():
    draft=Draft(item=Item(type='jeans'),claims=[],code_read=None,listing_text_en='Jeans',
        coverage=[ViewCoverage(region='front',status='shown',garment_outline=OUTLINE,
            evidence=[Box(frame_id='missing',box_2d=[0,0,1000,1000]),Box(frame_id='f2',box_2d=[0,0,1000,1000])])])
    assert coverage_report(draft,{'f2'})['views'][0]['garment_outline']==[]


def test_mask_belongs_only_to_first_frame_and_excludes_background(tmp_path):
    image=tmp_path/'frame.jpg';cv2.imwrite(str(image),np.full((200,200,3),100,np.uint8))
    coverage={'views':[{'region':'front','status':'shown','garment_outline':OUTLINE,
        'evidence':[{'frame_id':'f1'},{'frame_id':'f2'}]}]}
    masks=reference_masks(coverage,{'f1':image,'f2':image})
    assert set(masks)=={'f1'}
    assert masks['f1'][0,0]==0 and masks['f1'][100,100]==255


def test_background_features_cannot_align_textureless_garment(tmp_path):
    rng=np.random.default_rng(4);image=rng.integers(0,255,(500,500,3),dtype=np.uint8)
    image=cv2.GaussianBlur(image,(3,3),0)
    image[150:350,150:350]=130
    ref=tmp_path/'ref.jpg';received=tmp_path/'received.jpg'
    cv2.imwrite(str(ref),image);cv2.imwrite(str(received),image)
    mask=np.zeros((500,500),np.uint8);mask[190:310,190:310]=255
    assert align(ref,received).ok  # shared background easily passes
    assert not align(ref,received,reference_mask=mask).ok  # no garment correspondence


def test_missing_outline_prevents_consistent_production_assessment(tmp_path,monkeypatch):
    record=ConditionRecord(id='item',item=Item(type='shirt'),claims=[],
        capture=Capture(code_expected='',code_seen=False,take_sha256='hash',frames=['f1']))
    monkeypatch.setattr(gate,'_near_identical',lambda *a:False)
    monkeypatch.setattr(gate,'align',lambda *a:SimpleNamespace(ok=True,warped_path=Path('warp'),method='akaze'))
    monkeypatch.setattr(gate,'change_regions',lambda *a,**k:[])
    result=gate.check(record,{'f1':Path('ref')},[('f1',Path('new'))],tmp_path/'work',require_garment_focus=True)
    assert result.verdict=='cant_tell' and any('no usable garment outline' in s for s in result.limitations)


def test_garment_guidance_does_not_infer_defect_absence():
    draft=Draft(item=Item(type='trousers'),claims=[],code_read=None,listing_text_en='Trousers')
    report=coverage_report(draft,set())
    assert any('hips and pockets' in text for text in report['detail_requests'])
    assert report['needs_more_evidence']


def test_supplementary_photo_reaches_drafter_and_is_retained(tmp_path,monkeypatch):
    from fieldwork.store import LocalStore
    store=LocalStore(tmp_path/'store');monkeypatch.setattr(pipeline,'store',store)
    source=tmp_path/'take.mp4';source.write_bytes(b'original video')
    photo=tmp_path/'closeup.jpg';cv2.imwrite(str(photo),np.full((100,100,3),120,np.uint8))
    frame=tmp_path/'overview.jpg';cv2.imwrite(str(frame),np.full((100,100,3),100,np.uint8))
    monkeypatch.setattr('fieldwork.video.validate_video',lambda path:1.)
    monkeypatch.setattr(pipeline.fr,'extract_frames',lambda *a:[])
    monkeypatch.setattr(pipeline.fr,'evidence_candidates',lambda *a,**k:[SimpleNamespace(path=frame,t=0.)])
    seen=[]
    def draft(video,frames):
        seen.extend(fid for fid,_ in frames)
        return Draft(item=Item(type='trousers'),claims=[],code_read=None,listing_text_en='Trousers',
            coverage=[ViewCoverage(region='front',status='shown',evidence=[Box(frame_id='p1',box_2d=[0,0,1000,1000])])])
    monkeypatch.setattr(pipeline,'draft_record',draft)
    monkeypatch.setattr(pipeline.gr,'grade',lambda *a:{'condition':{'set':[3]}})
    monkeypatch.setattr(pipeline,'translate',lambda *a:{})
    record=pipeline.run_take(source,None,photos=[photo],item_id='mixed')
    assert seen==['f1','p1']
    assert 'p1' in record.capture.frames
    assert store.get_file('mixed','p1.jpg').read_bytes()==photo.read_bytes()
    assert store.get_file('mixed','take.mp4').read_bytes()==source.read_bytes()
