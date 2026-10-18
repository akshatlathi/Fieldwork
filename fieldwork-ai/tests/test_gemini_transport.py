"""A transient connection loss must not discard an entire inspection immediately."""
from types import SimpleNamespace
import httpx
import pytest

from fieldwork import gemini


def test_transient_disconnect_retries_without_repeating_other_work(monkeypatch):
    calls=[]
    def generate(**kwargs):
        calls.append(kwargs['model'])
        if len(calls)==1:raise httpx.RemoteProtocolError('Disconnected')
        return SimpleNamespace(usage_metadata=None)
    monkeypatch.setattr(gemini,'client',lambda:SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
    monkeypatch.setattr(gemini.config,'MODEL_FALLBACKS',[])
    monkeypatch.setattr(gemini.time,'sleep',lambda *a:None)
    monkeypatch.setattr(gemini,'_log',lambda *a:None)
    assert gemini.generate('test',[],model='test-model') is not None
    assert calls==['test-model','test-model']


def test_repeated_disconnect_remains_bounded(monkeypatch):
    calls=[]
    def generate(**kwargs):
        calls.append(kwargs['model']);raise httpx.RemoteProtocolError('Disconnected')
    monkeypatch.setattr(gemini,'client',lambda:SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
    monkeypatch.setattr(gemini.config,'MODEL_FALLBACKS',[])
    monkeypatch.setattr(gemini.time,'sleep',lambda *a:None)
    with pytest.raises(httpx.RemoteProtocolError):gemini.generate('test',[],model='test-model')
    assert len(calls)==2
