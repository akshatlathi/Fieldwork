/* Local design-preview fixtures. Disabled unless FIELDWORK_DESIGN_PREVIEW=1.
   No model, real payment, production store or external service is called. */
import {readFile} from "node:fs/promises";
import path from "node:path";
import type {ConditionRecord,IssueReport,Listing,Mandate,SellerDraft} from "@/lib/api";
export const dynamic="force-dynamic";
const stamp=()=>new Date().toISOString();
const fixture=(id="sample_bomber"):ConditionRecord=>({spec:"fieldwork.design-example/v1",id,item:{type:"Leather bomber",brand:null,size_label:"M",colour:null,material:"Leather · seller-declared"},claims:[
 {id:"cuff",lane:"shown",code:"cuff_visible",region:"left_cuff",severity:"none",note:"The ribbed cuff is visible in this view.",evidence:[{frame_id:"front",box_2d:[710,45,805,225]}],value:null,error:null},
 {id:"seller",lane:"declared",code:"wear_history",region:"whole",severity:"none",note:"Worn for two seasons · illustrative seller statement.",evidence:[],value:null,error:null},
 {id:"lining",lane:"cant_judge",code:"lining_not_shown",region:"back",severity:"none",note:"The inner lining is not shown.",evidence:[],value:null,error:null}],grade_set:[],price_band:[4800,4800],currency:"JPY",capture:{code_seen:false,frames:["front"],created_at:"2026-10-18T10:00:00Z"},listing_text_en:"Illustrative leather bomber for design review. The product image is generated; it is not inspected evidence from a real sale."});
const list=(id:string,status="published"):Listing=>({id,en:fixture(id).listing_text_en,publication_status:status,seller_limitations:["Inner lining not shown.","Design preview: images and records are illustrative."],capture_coverage:{views:[{region:"front",status:"shown",note:"Sample image",evidence:[]},{region:"back",status:"not_shown",note:"Additional view needed",evidence:[]},{region:"label",status:"not_shown",note:"Additional view needed",evidence:[]}],needs_more_evidence:true,guidance:["Add a back view and a readable care-label photo."],limitation:"Preview fixture, not an AI inspection."}});
let draft:SellerDraft={id:"sample_draft",status:"draft",revision:1,answer:null,issues:[],record:fixture("sample_draft"),limitations:list("sample_draft").seller_limitations!,guidance:["Add a back view and a readable care-label photo."],attempts:[],history:[]};
const mandates=new Map<string,Mandate>();const issues=new Map<string,IssueReport>();
const json=(body:unknown,status=200)=>Response.json(body,{status,headers:{"Cache-Control":"no-store"}});
async function handle(req:Request,params:Promise<{segments:string[]}>){
 if(process.env.FIELDWORK_DESIGN_PREVIEW!=="1")return json({detail:"Not found"},404);
 const {segments:s}=await params;const method=req.method;const url=new URL(req.url);const id=s[1]??"";
 if(s[0]==="media"){const bytes=await readFile(path.join(process.cwd(),"public/illustrations/leather-bomber.png"));return new Response(bytes,{headers:{"Content-Type":"image/png"}});}
 if(method==="GET"){
  if(s[0]==="search")return json(["sample_bomber",...(draft.status==="published"?[draft.id]:[])].map(i=>({id:i,item:fixture(i).item,grade_set:[],price_band:[4800,4800],currency:"JPY",shown_flaws:[],cant_judge:["lining"],evidence_badge:"Illustrative example",summary_line:"Design preview · sample data"})));
  if(s[0]==="records")return json(id===draft.id?draft.record:fixture(id));
  if(s[0]==="listings")return json(list(id,id===draft.id?draft.status:"published"));
  if(s[0]==="seller"&&s[1]==="drafts")return json(draft);
  if(s[0]==="escrow")return mandates.has(id)?json(mandates.get(id)):json({detail:"Unknown preview purchase"},404);
  if(s[0]==="issues")return id?(issues.has(id)?json(issues.get(id)):json({detail:"Unknown preview issue"},404)):json([...issues.values()].filter(i=>!url.searchParams.get("item_id")||i.item_id===url.searchParams.get("item_id")));
  if(s[0]==="review")return req.headers.get("Authorization")==="Bearer preview-review"?json([...issues.values()]):json({detail:"Use preview-review for the isolated design-preview queue."},401);
 }
 if(method!=="POST")return json({detail:"Not found"},404);
 const multipart=req.headers.get("content-type")?.includes("multipart/form-data");const form=multipart?await req.formData():null;
 const body:Record<string,unknown>=form?Object.fromEntries(form.entries()):await req.json().catch(()=>({}));
 if(s[0]==="take"){draft={...draft,status:"draft",revision:draft.revision+1,answer:null,issues:[],attempts:[{id:"preview_attempt",status:"complete",created_at:stamp(),media:[{url:"/media/sample_draft/front.jpg",sha256:"illustrative-preview-only"}]}]};return json(draft.record);}
 if(s[0]==="seller"&&s[1]==="drafts"){
  if(Number(body.revision)!==draft.revision)return json({detail:"This draft changed. Reload the latest version before saving."},409);
  if(draft.status==="published")return json({detail:"This record is already published."},409);
  if(s[3]==="declarations"){
   const answer=body.answer;if(!["issues_reported","none_known","unknown"].includes(String(answer)))return json({detail:"Choose a condition answer."},422);
   draft={...draft,answer:answer as SellerDraft["answer"],issues:(body.issues??[]) as SellerDraft["issues"],revision:draft.revision+1};return json(draft);
  }
  if(s[3]==="evidence"){draft={...draft,revision:draft.revision+1,attempts:[...draft.attempts,{id:"preview_extra_"+Date.now(),status:"complete",created_at:stamp(),media:[]}]};return json(draft);}
  if(s[3]==="publish"){if(!draft.answer||body.acknowledge_limitations!==true)return json({detail:"Review the condition answer and acknowledge limitations."},409);draft={...draft,status:"published",revision:draft.revision+1};return json(draft);}
 }
 if(s[0]==="ask")return json({answer:"Preview answer: the ribbed cuff is visible in source front. These illustrative images do not establish overall condition.",lang:"en",state:"shown",claim_ids:["cuff"]});
 if(s[0]==="agent"&&s[1]==="chat")return json({text:"Design-preview result: this sample has a visible cuff and an unknown lining. Open its Pass to inspect the source. No live AI was called.",model:"design-fixture",tool_calls:[{tool:"search_garments",args:{type:"jacket"},result:[{id:"sample_bomber",item:fixture().item,grade_set:[],price_band:[4800,4800],currency:"JPY",shown_flaws:[],cant_judge:["lining"],evidence_badge:"Illustrative",summary_line:"Design sample"}]}]});
 if(s[0]==="escrow"&&s.length===1){if(body.item_id===draft.id&&draft.status!=="published")return json({detail:"Publish the reviewed draft before purchase."},409);if(body.amount!==4800||body.currency!=="JPY")return json({detail:"Amount and currency must match this preview listing."},422);const m:Mandate={id:"preview_hold_"+Date.now(),item_id:String(body.item_id),payer:"buyer",payee:"seller",amount:4800,currency:"JPY",status:"held",events:[{event:"held",at:stamp()}]};mandates.set(m.id,m);return json(m);}
 if(s[0]==="escrow"&&s[2]==="accept"){const m=mandates.get(id);if(!m)return json({detail:"Unknown hold"},404);if([...issues.values()].some(i=>i.mandate_id===id&&i.status!=="resolved"))return json({detail:"A person must review the open issue first."},409);m.status="released";return json(m);}
 if(s[0]==="issues"&&s.length===1){const mid=String(body.mandate_id??"")||null;const m=mid?mandates.get(mid):null;const item=String(body.item_id);const issue:IssueReport={id:"preview_issue_"+Date.now(),item_id:item,mandate_id:mid,created_at:stamp(),updated_at:stamp(),status:"awaiting_review",buyer_text:String(body.buyer_text??""),listing:fixture(item),amount:m?.amount??null,currency:"JPY",suggested_assessment:"cant_tell",summary:"Design-preview example: there is insufficient evidence for a condition comparison. A person reviews the issue.",limitations:["This is an illustrative fixture; no AI inspection was run."],inspection:null,media:[],history:[{event:"issue_saved",at:stamp()}],decision:null};issues.set(issue.id,issue);return json(issue);}
 if(s[0]==="issues"&&s[2]==="evidence"){const report=issues.get(id);if(!report)return json({detail:"Unknown issue"},404);report.status="awaiting_review";report.history.push({event:"additional_evidence_submitted",at:stamp()});return json(report);}
 if(s[0]==="issues"&&s[2]==="decision"){
  if(req.headers.get("Authorization")!=="Bearer preview-review")return json({detail:"Preview reviewer key required"},401);
  const report=issues.get(id);if(!report)return json({detail:"Unknown issue"},404);
  const action=String(body.action);if(!["release","refund","request_evidence"].includes(action)||!String(body.note??"").trim()||!String(body.reviewer??"").trim())return json({detail:"Choose an action, reviewer and reason."},422);
  const pct=Number(body.refund_pct);if(action==="refund"&&(!Number.isInteger(pct)||pct<1||pct>100))return json({detail:"Choose a refund from 1 to 100 percent."},422);
  report.decision={action:action as "release"|"refund"|"request_evidence",refund_pct:action==="refund"?pct:0,reviewer:String(body.reviewer),note:String(body.note),at:stamp()};report.status=action==="request_evidence"?"needs_evidence":"resolved";
  if(report.mandate_id&&action!=="request_evidence"){const m=mandates.get(report.mandate_id);if(m)m.status=action==="release"?"released":pct===100?"refunded":"partial";}return json(report);
 }
 return json({detail:"Not found"},404);
}
type Context={params:Promise<{segments:string[]}>};
export const GET=(req:Request,c:Context)=>handle(req,c.params);
export const POST=(req:Request,c:Context)=>handle(req,c.params);
