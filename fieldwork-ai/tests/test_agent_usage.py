"""Do not count streamed partials or tool events as extra model responses."""
import json
import asyncio
import importlib
from types import SimpleNamespace
import pytest
from fieldwork import gemini


def test_agent_usage_skips_partials_and_tool_events(tmp_path,monkeypatch):
    monkeypatch.setattr(gemini.config,"LOG_DIR",tmp_path)
    usage=SimpleNamespace(prompt_token_count=7,candidates_token_count=2,thoughts_token_count=3)
    assert not gemini.log_agent_event("agent_buyer","test-model",SimpleNamespace(partial=True,usage_metadata=usage),1)
    assert not gemini.log_agent_event("agent_buyer","test-model",SimpleNamespace(partial=False,usage_metadata=None),1)
    assert gemini.log_agent_event("agent_buyer","test-model",SimpleNamespace(partial=False,usage_metadata=usage),2)
    rows=[json.loads(line) for line in (tmp_path/"cost.jsonl").read_text().splitlines()]
    assert len(rows)==1
    assert rows[0]["in_tokens"]==7 and rows[0]["out_tokens"]==2 and rows[0]["thinking_tokens"]==3
    assert rows[0]["task"]=="agent_buyer" and rows[0]["seconds"]==2


@pytest.mark.parametrize("name",["buyer","seller"])
def test_agent_runner_records_response_usage(tmp_path,monkeypatch,name):
    module=importlib.import_module(f"fieldwork.agents.{name}")
    monkeypatch.setattr(gemini.config,"LOG_DIR",tmp_path)
    event=SimpleNamespace(partial=False,
        usage_metadata=SimpleNamespace(prompt_token_count=9,candidates_token_count=1,thoughts_token_count=0),
        get_function_calls=lambda:[],get_function_responses=lambda:[],is_final_response=lambda:True,
        content=SimpleNamespace(parts=[SimpleNamespace(text="done")]))
    async def events(**kwargs):yield event
    monkeypatch.setattr(module,"_runner",lambda model:SimpleNamespace(run_async=events))
    assert asyncio.run(module._run("fixture-model","session","question"))["text"]=="done"
    row=json.loads((tmp_path/"cost.jsonl").read_text())
    assert row["task"]==f"agent_{name}" and row["in_tokens"]==9
