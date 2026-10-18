"""Both HTTP and agent purchases must respect the seller's price constraints."""
import pytest
from fastapi.testclient import TestClient
from fieldwork import api, escrow, pricing
from fieldwork.agents import mcp_server
from fieldwork.spec import Capture, ConditionRecord, Item
from fieldwork.store import LocalStore


@pytest.fixture
def purchase(tmp_path,monkeypatch):
    storage=LocalStore(tmp_path)
    for module in (api,escrow,mcp_server):monkeypatch.setattr(module,"store",storage)
    record=ConditionRecord(id="jacket",item=Item(type="jacket"),claims=[],price_band=(6000,6000), currency="INR",
                           capture=Capture(code_expected="test",code_seen=False,take_sha256="test"))
    storage.put_json("records",record.id,record.model_dump(mode="json"))
    storage.put_json("listings",record.id,{"id":record.id,"price_source":"seller","asking_price":6000,"negotiation_enabled":True,"currency":"INR"})
    storage.put_json("floors",record.id,{"floor":4500})
    return TestClient(api.app),storage,record


@pytest.mark.parametrize("amount",[0,-1])
def test_nonpositive_amount_rejected(purchase,amount):
    client,storage,_=purchase
    assert client.post("/escrow",json={"item_id":"jacket","amount":amount}).status_code==422
    assert storage.list_json("mandates")==[]


@pytest.mark.parametrize("amount",[100,3000,4499,6001])
def test_http_and_agent_cannot_bypass_seller_floor_or_band(purchase,amount):
    client,storage,_=purchase
    assert client.post("/escrow",json={"item_id":"jacket","amount":amount}).status_code==409
    with pytest.raises(ValueError,match="accepted range"):
        mcp_server.create_escrow("jacket","buyer",amount)
    assert storage.list_json("mandates")==[]


def test_currency_and_missing_price_rejected(purchase):
    client,storage,record=purchase
    assert client.post("/escrow",json={"item_id":"jacket","amount":5000,"currency":"USD"}).status_code==409
    listing=storage.get_json("listings",record.id);listing.pop("asking_price");storage.put_json("listings",record.id,listing)
    record.price_band=None
    storage.put_json("records",record.id,record.model_dump(mode="json"))
    assert client.post("/escrow",json={"item_id":"jacket","amount":5000}).status_code==409
    assert storage.list_json("mandates")==[]


def test_valid_floor_price_creates_held_mandate(purchase):
    client,storage,_=purchase
    quote=pricing.offer(storage,"jacket",4500)
    response=client.post("/escrow",json={"item_id":"jacket","amount":4500,"currency":"inr","quote_id":quote["quote_id"]})
    assert response.status_code==200
    assert response.json()["status"]=="held" and response.json()["currency"]=="INR"
    assert len(storage.list_json("mandates"))==1


def test_seller_floor_above_band_means_no_deal(purchase):
    client,storage,_=purchase
    storage.put_json("floors","jacket",{"floor":7000})
    assert client.post("/escrow",json={"item_id":"jacket","amount":6000}).status_code==409
    assert storage.list_json("mandates")==[]
