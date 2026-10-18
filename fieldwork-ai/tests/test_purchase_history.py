"""Recover purchases and saved seller drafts independently of browser state."""
import pytest
from fastapi.testclient import TestClient
from fieldwork import api, human_review
from fieldwork.store import LocalStore
from fieldwork.spec import ConditionRecord, Item, Capture


@pytest.fixture
def history(tmp_path, monkeypatch):
    storage=LocalStore(tmp_path/'store')
    monkeypatch.setattr(api,'store',storage);monkeypatch.setattr(human_review,'store',storage)
    record=ConditionRecord(id='lower',item=Item(type='sweatpants',brand='xFisics',colour='charcoal'),claims=[],
        capture=Capture(code_expected='secret',code_seen=False,take_sha256='hash'))
    storage.put_json('records','lower',record.model_dump(mode='json'))
    storage.put_json('floors','lower',{'floor':333})
    return TestClient(api.app),storage,record


def test_held_purchase_visible_without_browser_local_storage(history):
    client,storage,_=history
    storage.put_json('mandates','md_400',{'id':'md_400','item_id':'lower','amount':400,'currency':'INR',
        'status':'held','signature':'not-needed-in-history','events':[{'event':'held','t':200}]})
    storage.put_json('mandates','md_old',{'id':'md_old','item_id':'lower','amount':500,'currency':'INR',
        'status':'refunded','events':[{'event':'held','t':100}]})
    storage.put_json('mandates','orphan',{'id':'orphan','item_id':'missing','amount':100,'currency':'INR','status':'held'})
    response=client.get('/purchases');assert response.status_code==200
    purchases=response.json();assert [m['id'] for m in purchases]==['md_400','md_old']
    assert purchases[0]['amount']==400 and purchases[0]['status']=='held'
    assert purchases[0]['item']['type']=='sweatpants'
    assert '333' not in response.text and 'signature' not in response.text and 'secret' not in response.text


def test_purchase_history_attaches_the_exact_review_report(history):
    client,storage,record=history
    storage.put_json('mandates','md_400',{'id':'md_400','item_id':'lower','amount':400,'currency':'INR','status':'held','events':[]})
    report=human_review.IssueReport(id='issue_exact',item_id='lower',mandate_id='md_400',created_at=human_review.now(),
        updated_at=human_review.now(),listing=record.public().model_dump(mode='json'),currency='INR',status='awaiting_review')
    human_review.save(report)
    assert client.get('/purchases').json()[0]['issue_id']=='issue_exact'
    assert client.get('/purchases').json()[0]['issue_status']=='awaiting_review'


def test_resumable_drafts_have_no_private_price_limits(history):
    client,storage,_=history
    storage.put_json('seller_drafts','lower',{'id':'lower','status':'draft','asking_price':400,
        'history':[{'at':'2026-10-18T14:00:00Z'}]})
    storage.put_json('seller_drafts','failed',{'id':'failed','status':'draft','history':[]})
    response=client.get('/seller/drafts');assert response.status_code==200
    assert [d['id'] for d in response.json()]==['lower']
    assert response.json()[0]['asking_price']==400
    assert '333' not in response.text and 'floor' not in response.text and 'minimum' not in response.text
