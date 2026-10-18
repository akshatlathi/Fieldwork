"""Seller approval boundary, disclosures and immutable retake evidence."""
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from fieldwork import api, escrow, market, seller_review
from fieldwork.spec import Box, Capture, Claim, ConditionRecord, Item, Lane
from fieldwork.store import LocalStore
from fieldwork.take import pipeline


@pytest.fixture
def setup(tmp_path, monkeypatch):
    storage = LocalStore(tmp_path/'store')
    for module in (api, escrow, market, pipeline):
        monkeypatch.setattr(module, 'store', storage)
    calls=[]
    def inspect(video, code, photos, item_id, *, attempt_id, translate_listing):
        calls.append((video,photos,attempt_id))
        fid=attempt_id+'_p1';source=photos[-1]
        storage.put_file(item_id,source,fid+'.jpg')
        record=ConditionRecord(id=item_id,item=Item(type='trousers'),price_band=(100,500),
            capture=Capture(code_expected=code or '',code_seen=False,take_sha256='hash',frames=[fid]),
            claims=[Claim(id='c1',lane=Lane.shown,code='no_flaw_visible',region='back',note='No holes anywhere.',
                evidence=[Box(frame_id=fid,box_2d=[0,0,1000,1000])])],listing_text_en='Guaranteed hole-free.')
        storage.put_json('records',item_id,record.model_dump(mode='json'))
        storage.put_json('listings',item_id,{'id':item_id,'en':record.listing_text_en,'ja':'stale clean prose',
            'publication_status':'draft','capture_coverage':{'views':[{'region':'back','status':'shown'}],
                'guidance':['Unfold the fabric and add close-ups.']}})
        return record
    monkeypatch.setattr(pipeline,'run_take',inspect)
    monkeypatch.setattr(pipeline,'translate',lambda text:{'ja':'Translated: '+text})
    return TestClient(api.app),storage,calls


def capture(client):
    response=client.post('/take',files={'photos':('overview.jpg',b'original photo','image/jpeg')})
    assert response.status_code==200
    return response.json()['id']


def disclosure(client,item,revision=1):
    return client.post(f'/seller/drafts/{item}/declarations',json={'revision':revision,'answer':'issues_reported',
        'issues':[{'code':'hole','region':'back','description':'Hole hidden under a fold near the pocket.'}]})


def test_new_capture_is_hidden_and_cannot_be_purchased(setup):
    client,storage,_=setup;item=capture(client)
    assert client.get('/search').json()==[]
    with pytest.raises(ValueError,match='review and publish'):
        escrow.create(item,'buyer','seller',200,'INR')
    draft=client.get(f'/seller/drafts/{item}').json()
    assert draft['status']=='draft' and draft['revision']==1
    assert 'Guaranteed' not in draft['record']['listing_text_en']
    assert 'No holes anywhere' not in str(draft['record']['claims'])


def test_hidden_disclosure_stays_declared_after_reinspection_and_publication(setup):
    client,storage,calls=setup;item=capture(client)
    draft=disclosure(client,item).json()
    first=storage.get_json('seller_drafts',item)['attempts'][0]
    first_frame=first['record']['capture']['frames'][0]
    old_bytes=storage.get_file(item,first_frame+'.jpg').read_bytes()
    result=client.post(f'/seller/drafts/{item}/evidence',data={'revision':draft['revision']},
        files={'photos':('closeup.jpg',b'new closeup','image/jpeg')})
    assert result.status_code==200;draft=result.json()
    assert len(draft['attempts'])==2 and draft['issues'][0]['code']=='hole'
    assert len(calls[-1][1])==2  # earlier photo participates in reinspection
    assert storage.get_file(item,first_frame+'.jpg').read_bytes()==old_bytes
    claim=next(c for c in draft['record']['claims'] if c['id']=='seller_issue_1')
    assert claim['lane']=='declared' and claim['evidence']==[]
    assert any('reported hole' in text for text in draft['guidance'])
    assert client.get('/search').json()==[]
    draft=client.post(f'/seller/drafts/{item}/price',json={'revision':draft['revision'],'asking_price':200}).json()
    response=client.post(f'/seller/drafts/{item}/publish',json={'revision':draft['revision'],'acknowledge_limitations':True})
    assert response.status_code==200
    assert client.get('/search').json()[0]['id']==item
    assert client.get('/search?exclude_defects=hole').json()==[]
    listing=client.get(f'/listings/{item}').json()
    assert listing['publication_status']=='published'
    assert 'hidden under a fold' in listing['en'] and 'hidden under a fold' in listing['ja']
    assert listing['seller_limitations']
    assert escrow.create(item,'buyer','seller',200,'INR').status=='held'


def test_publication_requires_answer_acknowledgment_and_current_revision(setup):
    client,_,_=setup;item=capture(client)
    path=f'/seller/drafts/{item}/publish'
    assert client.post(path,json={'revision':1,'acknowledge_limitations':True}).status_code==409
    draft=disclosure(client,item).json()
    assert client.post(path,json={'revision':draft['revision']}).status_code==409
    assert client.post(path,json={'revision':1,'acknowledge_limitations':True}).status_code==409
    assert client.post(path,json={'revision':draft['revision'],'acknowledge_limitations':True}).status_code==409
    draft=client.post(f'/seller/drafts/{item}/price',json={'revision':draft['revision'],'asking_price':200}).json()
    assert client.post(path,json={'revision':draft['revision'],'acknowledge_limitations':True}).status_code==200
    assert disclosure(client,item,revision=draft['revision']+1).status_code==409


def test_failed_retake_retains_previous_evidence_and_disclosures(setup,monkeypatch):
    client,storage,_=setup;item=capture(client);draft=disclosure(client,item).json()
    before=draft['record']
    def fail(*a,**k):raise RuntimeError('Model unavailable')
    monkeypatch.setattr(pipeline,'run_take',fail)
    result=client.post(f'/seller/drafts/{item}/evidence',data={'revision':draft['revision']},
        files={'photos':('new.jpg',b'failed attempt evidence','image/jpeg')})
    assert result.status_code==200
    draft=result.json()
    assert draft['record']==before and draft['issues']
    assert draft['attempts'][-1]['status']=='failed'
    source=draft['attempts'][-1]['media'][0]['url']
    assert client.get(source).content==b'failed attempt evidence'
    assert len(storage.get_json('seller_drafts',item)['photos'])==1


def test_unsafe_stale_translation_is_not_revived(setup,monkeypatch):
    client,storage,_=setup;item=capture(client)
    def fail(*a):raise RuntimeError('Translation unavailable')
    monkeypatch.setattr(pipeline,'translate',fail)
    assert disclosure(client,item).status_code==200
    listing=storage.get_json('listings',item)
    assert 'ja' not in listing and listing['translation_unavailable']
    assert 'Seller reports hole' in listing['en']


def test_inconsistent_or_empty_disclosures_are_rejected(setup):
    client,_,_=setup;item=capture(client)
    path=f'/seller/drafts/{item}/declarations'
    assert client.post(path,json={'revision':1,'answer':'issues_reported','issues':[]}).status_code==422
    assert client.post(path,json={'revision':1,'answer':'issues_reported','issues':[{'code':'hole','description':'   '}]}).status_code==422


def test_retake_cannot_erase_previously_observed_defect(setup):
    client,storage,_=setup;item=capture(client)
    meta=storage.get_json('seller_drafts',item)
    old=meta['attempts'][0]['record']['claims'][0]
    old.update(code='hole',severity='minor',note='Small hole visible in the first capture.')
    old_frame=old['evidence'][0]['frame_id']
    storage.put_json('seller_drafts',item,meta)
    response=client.post(f'/seller/drafts/{item}/evidence',data={'revision':1},
        files={'photos':('folded.jpg',b'folded view without visible defect','image/jpeg')})
    assert response.status_code==200
    record=response.json()['record']
    retained=[c for c in record['claims'] if c['code']=='hole' and c['lane']=='shown']
    assert len(retained)==1 and retained[0]['note'].startswith('Earlier capture:')
    assert old_frame in record['capture']['frames']
