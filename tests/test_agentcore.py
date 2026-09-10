"""The AgentCore Runtime entrypoint: the contract, not the model calls."""
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from ninetyninety import agentcore
from ninetyninety.prepare import Form990EZ

CSV = "date,description,amount\n2025-01-08,ONLINE DONATION STRIPE PAYOUT,1250.00\n"


@pytest.fixture
def server():
    """The real handler on a real socket, so the wire format is what is tested."""
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), agentcore.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def get(url):
    with urllib.request.urlopen(url, timeout=10) as response:
        return response.status, json.loads(response.read())


def post(url, body):
    request = urllib.request.Request(
        url, data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def test_ping_reports_healthy(server):
    # AgentCore keeps the session alive only while /ping answers 200.
    assert get(f"{server}/ping") == (200, {"status": "Healthy"})


def test_unknown_paths_are_404(server):
    with pytest.raises(urllib.error.HTTPError) as raised:
        get(f"{server}/health")  # AgentCore pings /ping, nothing else
    assert raised.value.code == 404
    assert post(f"{server}/invoke", {"input": {}})[0] == 404


def test_invocations_returns_the_assembled_form(server, monkeypatch):
    seen = {}

    def fake_prepare(transactions, **kwargs):
        seen["rows"] = [t.description for t in transactions]
        seen["kwargs"] = kwargs
        form = Form990EZ()
        form.totals = {"line9": 1250, "line17": 0, "line18": 1250}
        return form

    monkeypatch.setattr(agentcore, "prepare_ledger", fake_prepare)
    status, body = post(f"{server}/invocations", {"input": {"ledger_csv": CSV}})
    assert status == 200
    assert body["output"]["totals"]["line9"] == 1250
    assert body["output"]["skipped"] == []
    assert seen["rows"] == ["ONLINE DONATION STRIPE PAYOUT"]
    # The row cap is enforced before any model call, and one draft at a time.
    assert seen["kwargs"] == {"max_rows": agentcore.MAX_ROWS, "exclusive": True}


def test_bad_requests_are_400_not_500(server):
    assert post(f"{server}/invocations", {})[0] == 400
    assert post(f"{server}/invocations", {"input": {"ledger_csv": ""}})[0] == 400
    # A CSV with no description/amount columns: load_ledger's ValueError, not a crash.
    status, body = post(f"{server}/invocations", {"input": {"ledger_csv": "a,b\n1,2\n"}})
    assert status == 400 and "amount" in body["error"]


def test_a_failed_draft_is_500_with_the_reason(server, monkeypatch):
    def boom(transactions, **kwargs):
        raise RuntimeError("Gemini is not configured")

    monkeypatch.setattr(agentcore, "prepare_ledger", boom)
    status, body = post(f"{server}/invocations", {"input": {"ledger_csv": CSV}})
    assert status == 500 and "Gemini is not configured" in body["error"]


def test_handle_passes_a_caller_supplied_row_cap_through(monkeypatch):
    seen = {}
    monkeypatch.setattr(agentcore, "prepare_ledger",
                        lambda tx, **kw: seen.update(kw) or Form990EZ())
    agentcore.handle({"input": {"ledger_csv": CSV, "max_rows": 3}})
    assert seen["max_rows"] == 3
