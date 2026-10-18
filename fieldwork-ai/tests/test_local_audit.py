"""Buyer media, negotiation enforcement and mismatched-region regressions."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from fieldwork import api, escrow, market, pricing, seller_review, human_review
from fieldwork.agents import mcp_server, seller
from fieldwork.spec import Box, Capture, Claim, ConditionRecord, Item, Lane, Severity
from fieldwork.store import LocalStore
from fieldwork.unbox import gate
from fieldwork.unbox.diff import crop_pair, comparable_box


@pytest.fixture
def shop(tmp_path, monkeypatch):
    storage = LocalStore(tmp_path / "store")
    for module in (api, escrow, market, human_review, mcp_server, seller):
        monkeypatch.setattr(module, "store", storage)
    record = ConditionRecord(id="tee", item=Item(type="t-shirt", brand="celio*"), claims=[], currency="INR",
        grade_set=[2, 3, 4], capture=Capture(code_expected="private", code_seen=False, take_sha256="hash", frames=["p1"]))
    storage.put_json("records", record.id, record.model_dump(mode="json"))
    storage.put_json("listings", record.id, {"id":record.id, "price_source":"seller", "asking_price":1500,
        "currency":"INR", "negotiation_enabled":True, "publication_status":"published"})
    storage.put_json("floors", record.id, {"floor":1200})
    return TestClient(api.app), storage, record


def test_private_minimum_never_in_search_listing_or_agent_response(shop):
    client, storage, record = shop
    card = client.get('/search?brand=celio&type=tshirt').json()[0]
    assert card['purchase_price'] == 1500 and card['price_band'] == [1500, 1500]
    assert card['media'][0]['url'].endswith('/p1.jpg')
    assert not client.get('/search?brand=other').json()
    assert not client.get('/search?min_grade=3').json()  # possible grade 4 is not minimum grade 3
    assert not client.get('/search?max_price=1400').json()
    for payload in (card, client.get('/listings/tee').json(), mcp_server.get_condition_record('tee')):
        assert '1200' not in str(payload) and 'floor' not in payload
    assert 'private' not in str(mcp_server.get_condition_record('tee'))


def test_negotiation_and_both_escrow_paths_enforce_floor_and_quote(shop):
    client, storage, _ = shop
    first = seller.propose_price('tee', 1000)
    assert first['status'] == 'counter' and first['price'] == 1250
    assert 'minimum' not in str(first) and 'floor' not in first
    second = client.post('/offers', json={'item_id':'tee', 'amount':1250, 'negotiation_id':first['negotiation_id']}).json()
    assert second['status'] == 'accepted' and second['round'] == 2
    for amount in (1100, 1200, 1250, 1501):
        assert client.post('/escrow', json={'item_id':'tee','amount':amount}).status_code == 409
        with pytest.raises(ValueError):
            mcp_server.create_escrow('tee','buyer',amount)
    response = client.post('/escrow', json={'item_id':'tee','amount':1250,'quote_id':second['quote_id']})
    assert response.status_code == 200 and response.json()['status'] == 'held'
    # Repeated confirmation cannot create another held purchase.
    assert client.post('/escrow', json={'item_id':'tee','amount':1250,'quote_id':second['quote_id']}).status_code == 409
    assert len(storage.list_json('mandates')) == 1


def test_negotiated_quote_can_be_confirmed_by_mcp(shop):
    _, storage, _ = shop
    quote = seller.propose_price('tee', 1300)
    result = mcp_server.create_escrow('tee','buyer',1300,'INR',quote['quote_id'])
    assert result['amount'] == 1300 and result['status'] == 'held'


def test_quote_expiry_wrong_item_and_round_limit(shop):
    client, storage, _ = shop
    quote = pricing.offer(storage, 'tee', 1250)
    saved = storage.get_json('quotes', quote['quote_id'])
    saved['expires_at'] = (datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
    storage.put_json('quotes', saved['id'], saved)
    assert client.post('/escrow', json={'item_id':'tee','amount':1250,'quote_id':saved['id']}).status_code == 409
    for _ in range(4):
        pricing.offer(storage, 'tee', 1100, quote['negotiation_id'])
    with pytest.raises(ValueError, match='five-round'):
        pricing.offer(storage, 'tee', 1100, quote['negotiation_id'])
    with pytest.raises(ValueError, match='Unknown negotiation'):
        pricing.offer(storage, 'tee', 1250, 'other-item-negotiation')


def test_fixed_price_and_no_heuristic_fallback(shop):
    client, storage, record = shop
    listing = storage.get_json('listings','tee'); listing['negotiation_enabled'] = False
    storage.put_json('listings','tee',listing)
    assert seller.propose_price('tee',1000)['status'] == 'fixed'
    assert client.post('/escrow',json={'item_id':'tee','amount':1200}).status_code == 409
    assert client.post('/escrow',json={'item_id':'tee','amount':1500}).status_code == 200
    listing.pop('price_source'); storage.put_json('listings','tee',listing)
    record.price_band=(500,5000); storage.put_json('records','tee',record.model_dump(mode='json'))
    assert client.get('/records/tee').json()['price_band'] is None
    assert client.get('/listings/tee').json()['purchase_price'] is None


def test_help_lists_actual_reports_without_reviewer_token(shop):
    client, storage, record = shop
    report = human_review.begin(record,'Hole on sleeve',None)
    human_review.complete(report.id, gate.UnboxResult('cant_tell'))
    assert client.get('/issues').json()[0]['id'] == report.id
    assert client.get('/issues?item_id=tee').json()[0]['status'] == 'awaiting_review'
    assert client.get('/review').status_code in (401,503)  # reviewer actions stay protected


def test_purchased_garment_is_not_advertised_for_another_purchase(shop):
    client,storage,_=shop
    assert client.post('/escrow',json={'item_id':'tee','amount':1500}).status_code==200
    assert client.get('/search').json()==[]
    assert not client.get('/listings/tee').json()['purchase_available']
    assert client.post('/offers',json={'item_id':'tee','amount':1300}).status_code==409


def test_replay_has_source_labels_and_both_images(shop, tmp_path):
    _, _, record = shop
    path = tmp_path/'received.jpg'; cv2.imwrite(str(path), np.full((80,80,3),120,np.uint8))
    result = gate.check(record, {'p1':path}, [('p1',path)], tmp_path/'crops', received_labels={str(path):'Received photo 2'})
    finding = result.findings[0]
    assert finding.listing_frame_id == 'p1' and finding.received_label == 'Received photo 2'
    assert finding.listing_crop and finding.unbox_crop and result.verdict == 'cant_tell'
    assert 'pixel-for-pixel' not in finding.what


def test_wrong_region_alignment_is_rejected_before_defect_judging(shop, tmp_path, monkeypatch):
    _, _, record = shop
    monkeypatch.setattr(gate, '_near_identical', lambda *a: False)
    monkeypatch.setattr(gate, 'align', lambda *a,**k: SimpleNamespace(ok=True,warped_path=tmp_path/'warp',garment_focused=True))
    monkeypatch.setattr(gate.judge, 'correspondence', lambda *a: gate.judge.Correspondence(comparable=False,reason='Neckline and side seam are different regions.'))
    monkeypatch.setattr(gate, 'change_regions', lambda *a,**k: pytest.fail('Do not diff mismatched views'))
    result = gate.check(record, {'p1':Path('ref')}, [('p1',Path('received'))],tmp_path/'work',require_garment_focus=True)
    assert result.pairs_aligned == 0 and result.verdict == 'cant_tell'
    assert result.comparisons[0]['kind'] == 'unmatched_view'


def test_mismatched_crop_never_becomes_missing_flaw(shop, tmp_path, monkeypatch):
    _, _, record = shop
    record.claims = [Claim(id='hole', lane=Lane.shown,code='hole',severity=Severity.minor,
        evidence=[Box(frame_id='p1',box_2d=[100,100,500,500])])]
    monkeypatch.setattr(gate, '_near_identical',lambda *a:False)
    monkeypatch.setattr(gate, 'align',lambda *a:SimpleNamespace(ok=True,warped_path=Path('warp')))
    monkeypatch.setattr(gate, 'crop_pair',lambda *a,**k:(Path('a'),Path('b')))
    monkeypatch.setattr(gate.judge,'flaw_still_there',lambda *a:gate.judge.FlawCheck(still_visible=False,unsure=False,comparable=False,reason='Different regions'))
    monkeypatch.setattr(gate,'change_regions',lambda *a,**k:[])
    result = gate.check(record,{'p1':Path('ref')},[('p1',Path('received'))],tmp_path/'work')
    assert result.verdict == 'cant_tell' and not result.findings
    assert result.comparisons[-1]['unsure']


def test_mismatched_change_never_becomes_new_defect(shop,tmp_path,monkeypatch):
    _,_,record=shop
    monkeypatch.setattr(gate,'_near_identical',lambda *a:False)
    monkeypatch.setattr(gate,'align',lambda *a:SimpleNamespace(ok=True,warped_path=Path('warp')))
    monkeypatch.setattr(gate,'crop_pair',lambda *a,**k:(Path('a'),Path('b')))
    monkeypatch.setattr(gate,'change_regions',lambda *a,**k:[SimpleNamespace(score=100,box_2d=[100,100,500,500])])
    monkeypatch.setattr(gate.judge,'compare',lambda *a:gate.judge.PairVerdict(comparable=False,new_defect=True,code='hole',severity='major',unsure=False,reason='Wrong regions'))
    result=gate.check(record,{'p1':Path('ref')},[('p1',Path('received'))],tmp_path/'work')
    assert result.verdict=='cant_tell' and not result.findings


def test_crops_cannot_silently_resize_or_use_unsupported_context(tmp_path):
    ref=tmp_path/'ref.png'; received=tmp_path/'new.png'
    cv2.imwrite(str(ref),np.full((100,100,3),100,np.uint8))
    cv2.imwrite(str(received),np.full((80,100,3),100,np.uint8))
    with pytest.raises(ValueError,match='coordinate system'):
        crop_pair(ref,received,[100,100,500,500])
    mask=np.zeros((100,100),np.uint8);mask[20:60,20:60]=255
    assert not comparable_box(mask,[200,200,600,600])  # inner box valid, padded surroundings unsupported
    assert comparable_box(mask,[300,300,400,400])


def test_seller_price_validation():
    from pydantic import ValidationError
    for body in ({'asking_price':1500,'currency':'JPY'},
                 {'asking_price':1500,'negotiation_enabled':True,'minimum_price':1501},
                 {'asking_price':1500,'negotiation_enabled':True},
                 {'asking_price':1500,'minimum_price':1200},
                 {'asking_price':0}, {'asking_price':1.5}):
        with pytest.raises(ValidationError):
            pricing.PriceIn(revision=1,**body)


def test_read_only_buyer_tools_do_not_offer_automatic_purchase():
    from fieldwork.agents import buyer
    agent=buyer._runner('test-model').agent
    names={tool.func.__name__ for tool in agent.tools}
    assert 'search_garments' in names and 'propose_price' in names and 'create_escrow' not in names


def test_buyer_ask_does_not_block_event_loop(monkeypatch):
    import asyncio, time
    from fieldwork.agents import buyer
    def slow(*args):time.sleep(.05); return {'state':'cant_judge'}
    monkeypatch.setattr(buyer.tools,'ask_garment',slow)
    async def exercise():
        pending=asyncio.create_task(buyer.ask_garment('tee','smell?'))
        await asyncio.sleep(.01)
        assert not pending.done()
        return await pending
    assert asyncio.run(exercise())['state']=='cant_judge'
