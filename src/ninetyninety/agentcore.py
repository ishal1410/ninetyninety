"""Amazon Bedrock AgentCore Runtime entrypoint for the NinetyNinety graph.

AgentCore's HTTP protocol contract (docs.aws.amazon.com/bedrock-agentcore,
"HTTP protocol contract"): host 0.0.0.0, port 8080, linux/arm64 container,
`POST /invocations` (JSON in, JSON out) and `GET /ping` (health) both required.

    request   {"input": {"ledger_csv": "date,description,amount\\n...",
                         "max_rows": 12}}
    response  {"output": {lines, totals, disagreements, low_confidence,
                          unclassified, unreviewed, ungrounded, trace, skipped}}

This exposes ONE bounded classification run, not the whole product. AgentCore
caps a synchronous request at 15 minutes and a ledger's runtime is set by
Gemini's free-tier daily caps, so the default is one batch (12 rows). Bigger
ledgers stay on the Streamlit app and the CLI.

ponytail: stdlib ThreadingHTTPServer, not FastAPI + uvicorn -- two endpoints
and no streaming do not earn a web framework, and the image stays at two
pinned dependencies. Move to FastAPI if /invocations ever needs SSE.
Threading is not optional: AgentCore polls /ping while an invocation runs, and
a single-threaded server would look unhealthy for the whole draft.
"""
import json
import os
import tempfile
import traceback
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .ledger import load_ledger
from .prepare import prepare_ledger

PORT = 8080
# Rows one invocation will accept. A knob, not a constant: how many rows fit
# in AgentCore's 15-minute request timeout depends on how much Gemini
# free-tier quota is left that day, which no code here can see.
MAX_ROWS = int(os.environ.get("AGENTCORE_MAX_ROWS", "12"))


def handle(payload: dict) -> dict:
    """The /invocations request body in, the response body out.

    Raises ValueError for anything the caller got wrong (answered as 400).
    """
    body = payload.get("input")
    if not isinstance(body, dict):
        raise ValueError('expected {"input": {"ledger_csv": "..."}}')
    csv_text = body.get("ledger_csv")
    if not isinstance(csv_text, str) or not csv_text.strip():
        raise ValueError("input.ledger_csv must be a non-empty CSV string")
    max_rows = body.get("max_rows", MAX_ROWS)

    skipped: list[dict] = []
    # load_ledger owns every CSV quirk already -- BOM, cp1252, delimiter
    # sniffing, invisible code points, accountant's negatives. Round-tripping
    # through a temp file reuses all of it instead of re-parsing here.
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "ledger.csv"
        path.write_text(csv_text, encoding="utf-8")
        transactions = load_ledger(path, skipped)
    if not transactions:
        raise ValueError("no usable rows in input.ledger_csv")

    form = prepare_ledger(transactions, max_rows=max_rows, exclusive=True)
    output = asdict(form)
    output["skipped"] = skipped
    return {"output": output}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"  # Content-Length is set on every reply

    def _send(self, code: int, body: dict) -> None:
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path.split("?")[0] == "/ping":
            # "Healthy", never "HealthyBusy": the draft runs inside the
            # /invocations request, so there is no background task to keep a
            # session alive for. time_of_last_update is omitted deliberately --
            # a timestamp that moves on every ping stops idle sessions ever
            # timing out, which is how you burn credits after judging.
            self._send(200, {"status": "Healthy"})
        else:
            self._send(404, {"error": f"no such path: {self.path}"})

    def do_POST(self):
        if self.path.split("?")[0] != "/invocations":
            self._send(404, {"error": f"no such path: {self.path}"})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:  # covers json.JSONDecodeError
            self._send(400, {"error": "request body is not JSON"})
            return
        if not isinstance(payload, dict):
            self._send(400, {"error": "request body is not a JSON object"})
            return
        try:
            self._send(200, handle(payload))
        except ValueError as bad_request:
            self._send(400, {"error": str(bad_request)})
        except Exception as failure:  # noqa: BLE001 - a failed draft must not
            # kill the container; AgentCore turns a 5xx into RuntimeClientError
            # and the reason belongs in CloudWatch, not in a stack trace to the
            # caller.
            traceback.print_exc()
            self._send(500, {"error": f"{type(failure).__name__}: {str(failure)[:500]}"})

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} {fmt % args}", flush=True)  # -> CloudWatch


def main() -> None:
    print(f"agentcore entrypoint listening on 0.0.0.0:{PORT}, max_rows={MAX_ROWS}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
