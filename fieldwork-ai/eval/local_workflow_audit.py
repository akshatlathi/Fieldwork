"""Live photo-to-human-review functional test, using an isolated local store.
This reuses the source image for the replay control; it is not a damage benchmark.
Requires Vertex/ADC, HF cache, FW_STORE_DIR and FW_REVIEW_TOKEN.
"""
import argparse, json, os, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fastapi.testclient import TestClient
from fieldwork.api import app
from fieldwork import config

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--photo",type=Path,required=True)
parser.add_argument("--out",type=Path,required=True)
args=parser.parse_args()
if (config.STORE_KIND != "local" or not os.getenv("FW_STORE_DIR") or not os.getenv("FW_REVIEW_TOKEN")
        or config.STORE_DIR.resolve() == (config.ROOT/"store").resolve()):
    raise SystemExit("Use an isolated FW_STORE_DIR and set FW_REVIEW_TOKEN.")
out=args.out;out.mkdir(parents=True,exist_ok=True)
source=args.photo
if not source.is_file():raise SystemExit("Source photo is missing.")
steps=[]
client=TestClient(app)
def call(name, method, route, **kwargs):
 t=time.monotonic(); response=getattr(client,method)(route,**kwargs)
 row={'step':name,'http':response.status_code,'seconds':round(time.monotonic()-t,2)}
 steps.append(row); print(json.dumps(row),flush=True)
 assert response.status_code==200, response.text[:400]
 return response.json()
def upload():return {'photos':(source.name,source.read_bytes(),'image/jpeg')}
try:
 record=call('seller_real_photo_capture','post','/take',files=upload())
 item=record['id']; assert record['price_band'] is None and record['currency']=='INR'
 draft=call('seller_condition_review','get',f'/seller/drafts/{item}')
 draft=call('seller_disclosure','post',f'/seller/drafts/{item}/declarations',json={'revision':draft['revision'],'answer':'unknown','issues':[]})
 draft=call('seller_INR_price_and_private_floor','post',f'/seller/drafts/{item}/price',json={'revision':draft['revision'],'asking_price':1500,'negotiation_enabled':True,'minimum_price':1200,'currency':'INR'})
 assert '1200' not in json.dumps(draft)
 call('seller_explicit_publication','post',f'/seller/drafts/{item}/publish',json={'revision':draft['revision'],'acknowledge_limitations':True})
 listing=call('buyer_listing_media','get',f'/listings/{item}')
 assert listing['asking_price']==1500 and listing['media']
 cards=call('buyer_search','get','/search')
 assert cards[0]['id']==item and cards[0]['purchase_price']==1500
 assert client.get(listing['media'][0]['url']).status_code==200
 quote=call('seller_rule_counteroffer','post','/offers',json={'item_id':item,'amount':1000})
 assert quote['price']==1250 and quote['status']=='counter'
 md=call('buyer_confirms_quote','post','/escrow',json={'item_id':item,'amount':1250,'currency':'INR','quote_id':quote['quote_id']})
 issue=call('received_evidence_and_review_report','post','/issues',data={'item_id':item,'mandate_id':md['id'],'buyer_text':'Audit: same source image reused, not an independent delivery capture.'},files=upload())
 assert issue['status']=='awaiting_review' and issue['suggested_assessment']=='cant_tell'
 assert all(f['listing_label'] and f['received_label'] for f in issue['inspection']['findings'])
 assert client.get(f'/escrow/{md["id"]}').json()['status']=='held'
 assert client.post(f'/escrow/{md["id"]}/accept').status_code==409
 history=call('help_pending_review_discovery','get','/issues');assert history[0]['id']==issue['id']
 headers={'Authorization':'Bearer '+os.environ['FW_REVIEW_TOKEN']}
 call('human_requests_evidence','post',f'/issues/{issue["id"]}/decision',headers=headers,json={'action':'request_evidence','reviewer':'Audit test actor','note':'Show the armpit in a new capture.'})
 update=call('buyer_additional_evidence','post',f'/issues/{issue["id"]}/evidence',files=upload())
 assert len(update['media'])>len(issue['media'])
 resolved=call('human_records_refund','post',f'/issues/{issue["id"]}/decision',headers=headers,json={'action':'refund','refund_pct':25,'reviewer':'Audit test actor','note':'Functional test of human review; not a real damage decision.'})
 assert resolved['status']=='resolved' and client.get(f'/escrow/{md["id"]}').json()['status']=='partial'
 result={'passed':True,'item_id':item,'issue_id':issue['id'],'scope':'Live seller model + local API workflow; same-image replay control, not damage accuracy or independent delivery evaluation','steps':steps,'report':resolved}
except Exception as exc:
 result={'passed':False,'error':str(exc),'steps':steps};raise
finally:
 (out/'live-workflow.json').write_text(json.dumps(result,indent=2))
