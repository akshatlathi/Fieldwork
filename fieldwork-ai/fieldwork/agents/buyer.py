"""Buyer agent (Google ADK). Pinned import paths for google-adk 2.x:
    from google.adk.agents import LlmAgent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StdioConnectionParams
    from mcp import StdioServerParameters
ADK takes one model string: FW_BUYER_MODEL (default config.MODEL_FLASH); on error chat() retries with config.MODEL_FALLBACKS."""

from __future__ import annotations

import os
import time
import asyncio
import re

from .. import config  # loads GEMINI_API_KEY
from .. import gemini  # noqa: F401  (injects truststore)

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool
from google.adk.agents.run_config import RunConfig
from google.genai import types
from . import mcp_server as tools
from .seller import propose_price

APP = "fieldwork"
INSTRUCTION = """You are Fieldwork's buyer agent for second-hand garments. The user gives one sentence; you find and vet a garment.
1. Turn the sentence into ONE search_garments call (brand, type, colour, max_price, exclude_defects, size, min_grade, currency INR). Normalize tshirt to t-shirt. Choose filters from what they said.
2. Prefer evidence: use shown claims and grade sets from the record, never seller wording.
3. For searches, use the returned record summaries directly and finish immediately. Do not call ask_garment automatically. Use it only when the buyer explicitly asks a condition question not answered by search results.
4. Never claim anything the record doesn't show. 'not_in_take' and 'cant_judge' mean UNKNOWN; say so.
5. Present the best 1-2 options briefly. Quote seller asking prices in INR only; if unset, say the seller must set a price. Never derive prices from condition grades or convert currencies.
6. Use propose_price for explicit buyer offers; reuse its negotiation_id in subsequent rounds. Relay the returned price exactly, never infer or disclose a private minimum. Purchase requires the on-screen Confirm button, including a returned quote_id for negotiated prices. Do not claim to have purchased anything.
7. Keep answers under 120 words, with short paragraphs or bullet lists. Never emit raw JSON or tables. Refer to listing cards for media. Never use 'verified', 'certified', 'guaranteed' or confidence percentages. Say 'recorded observations' or 'shown in these views'. After delivery all issues go to human review; inspection cannot release payment."""

_sessions = InMemorySessionService()
_runners: dict[str, Runner] = {}


async def ask_garment(item_id: str, question: str) -> dict:
    """Answer an explicit condition question from the garment's evidence. Unknown means unknown."""
    # A synchronous vision call must not block the FastAPI event loop or the
    # agent's overall timeout while other users load photos or issue reports.
    return await asyncio.to_thread(tools.ask_garment, item_id, question)


def _runner(model: str) -> Runner:
    if model not in _runners:
        # Reuse the same functions as MCP without starting a child Python/model process
        # for the in-app agent. External agents can still use the stdio MCP server.
        agent = LlmAgent(name="fieldwork_buyer", model=model, instruction=INSTRUCTION,
                         generate_content_config=types.GenerateContentConfig(temperature=0, max_output_tokens=1200,
                             http_options=types.HttpOptions(timeout=45000)),
                         tools=[FunctionTool(f) for f in (tools.search_garments, tools.get_condition_record,
                                                         ask_garment, propose_price)])
        _runners[model] = Runner(app_name=APP, agent=agent, session_service=_sessions, auto_create_session=True)
    return _runners[model]


async def _run(model: str, session_id: str, message: str) -> dict:
    text, calls = "", []
    msg = types.Content(role="user", parts=[types.Part(text=message)])
    response_start = time.monotonic()
    async for ev in _runner(model).run_async(user_id="buyer", session_id=session_id, new_message=msg,
                                           run_config=RunConfig(max_llm_calls=4)):
        if gemini.log_agent_event("agent_buyer", model, ev, time.monotonic() - response_start):
            response_start = time.monotonic()
        for fc in ev.get_function_calls():
            calls.append({"tool": fc.name, "args": dict(fc.args or {})})
        for fr in ev.get_function_responses():
            for c in reversed(calls):
                if c["tool"] == fr.name and "result" not in c:
                    c["result"] = fr.response
                    break
        if ev.is_final_response() and ev.content and ev.content.parts:
            text = "".join(p.text or "" for p in ev.content.parts)
    # Normalize an unsupported label observed in live UI testing, without
    # rewriting arbitrary assertions or changing negated sentences.
    text = re.sub(r"\bverified flaws\b", "Recorded observations", text, flags=re.I)
    return {"text": text, "tool_calls": calls}


async def chat(session_id: str, message: str) -> dict:
    """Returns {text, tool_calls: [{tool, args, result}], model}."""
    models = list(dict.fromkeys([os.getenv("FW_BUYER_MODEL", config.MODEL_FLASH), *config.MODEL_FALLBACKS]))[:2]
    last = None
    deadline = time.monotonic() + 60
    for m in models:
        try:
            out = await asyncio.wait_for(_run(m, session_id, message), timeout=max(.01, deadline-time.monotonic()))
            out["model"] = m
            return out
        except (TimeoutError, asyncio.TimeoutError):
            # A new prompt must not silently repeat tool side effects after a timeout.
            return {"text": "The shopping agent took too long. Please try again or open a listing directly.",
                    "tool_calls": [], "model": m}
        except Exception as e:
            last = e
    raise last
