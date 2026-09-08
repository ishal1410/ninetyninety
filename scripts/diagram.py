"""Render docs/architecture.png from an HTML/SVG layout via headless Chromium.

    python scripts/diagram.py

BOXES and ARROWS are the content contract checked by tests/test_diagram.py;
the HTML below is the presentation.
"""
import html
from pathlib import Path

W, H = 1600, 760

# The five things the hackathon FAQ says an architecture diagram must show.
BOXES = [
    ("User input / interface",
     ["A volunteer treasurer uploads the bank ledger as CSV",
      "Streamlit app (app.py) or CLI (cli.py)",
      "date, description, amount; whole dollars, money in +, money out -"]),
    ("Strands Agents graph, per batch of 12 rows",
     ["GraphBuilder: preparer and reviewer are blind parallel entry nodes",
      "Loop per node: model -> tools -> reasoning -> response",
      "Conditional edge to the referee only when their lines differ",
      "Python word-checks each quoted rule, Referee included, against the IRS text"]),
    ("Tools & integrations",
     ["@tool line_guidance returns the IRS 990-EZ Part I instruction text",
      "pydantic BatchCalls / Verdicts: structured output",
      "IRS e-file XML corpus: 3,632 real returns validate formmath.py"]),
    ("Model provider",
     ["Google Gemini through Strands' native GeminiModel (one provider, free tier)",
      "Per-model daily cap: rotates gemini-3.8-flash -> 3.5 -> 3.6 -> 3.7 -> 3.5-lite",
      "429 or 5xx: advertised-delay backoff, 3 attempts, next model, then surfaced",
      "Amazon Bedrock is the one-line swap once the account's quota is seeded"]),
    ("Output",
     ["Form 990-EZ Part I, every line citing its rows and the IRS rule",
      "Lines 9, 17, 18 computed in formmath.py, never by a model",
      "Disagreements, low confidence and unclassified rows all shown",
      "The real IRS f990ez.pdf filled, DRAFT notice on every page"]),
]

# (from box, to box, label) with boxes numbered 1-5 in BOXES order.
ARROWS = [(1, 2, "ledger rows"), (2, 3, "tool calls"), (4, 2, "model calls"), (2, 5, "classified rows")]

CSS = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
:root{--ink:#14213D;--paper:#FFFFFF;--tint:#F1F4F8;--rule:#9AA5B1;--green:#1B6B45;--aws:#FF9900;--muted:#5B6776}
*{box-sizing:border-box;margin:0}
html,body{width:1600px;height:760px;background:var(--paper);color:var(--ink);
  font-family:'IBM Plex Sans',system-ui,sans-serif;font-size:16px;line-height:1.35}
.page{position:relative;width:1600px;height:760px;padding:40px 48px}
h1{font-size:30px;font-weight:600;letter-spacing:-.01em}
h1 span{color:var(--muted);font-weight:400}
.sub{color:var(--muted);margin-top:4px;font-size:15px}
.box{position:absolute;background:var(--tint);border:1.5px solid var(--rule);border-radius:6px;padding:14px 18px}
.box h2{font-size:17px;font-weight:600;margin-bottom:8px}
.box ul{list-style:none;padding:0}
.box li{font-size:14px;color:var(--ink);padding-left:12px;text-indent:-12px;margin:3px 0}
.box li::before{content:'';display:inline-block;width:5px;height:5px;border-radius:50%;
  background:var(--rule);margin-right:7px;vertical-align:middle}
.aws{border-color:var(--aws);background:#FFF7EA}
.aws h2{color:#8A4B00}
.model{border-color:#1A73E8;background:#EEF4FF}
.model h2{color:#174EA6}
.graph{background:var(--paper);border:2px solid var(--ink);padding:0}
.graph h2{padding:14px 18px 0}
.graph ul{padding:0 18px 12px}
.graph .canvas{height:190px;margin:8px 18px 4px;position:relative}
.node{position:absolute;width:150px;height:44px;border:1.5px solid var(--ink);border-radius:22px;
  display:flex;align-items:center;justify-content:center;font-weight:500;font-size:15px;background:var(--paper)}
.node small{position:absolute;top:46px;left:0;right:0;text-align:center;font-size:12px;color:var(--muted);font-weight:400}
.tool{position:absolute;padding:4px 10px;border:1px dashed var(--green);border-radius:4px;color:var(--green);
  font-family:'IBM Plex Mono',monospace;font-size:12.5px;background:var(--paper)}
.canvas svg{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}
.lbl{font-size:12px;fill:#5B6776;font-family:'IBM Plex Sans',sans-serif}
"""


def _box(i, cls, style):
    head, lines = BOXES[i]
    items = "".join(f"<li>{html.escape(l)}</li>" for l in lines)
    return f'<div class="box {cls}" style="{style}"><h2>{html.escape(head)}</h2><ul>{items}</ul></div>'


def _graph_box():
    head, lines = BOXES[1]
    items = "".join(f"<li>{html.escape(l)}</li>" for l in lines)
    canvas = """
<div class="canvas">
  <svg viewBox="0 0 580 190" preserveAspectRatio="none">
    <defs><marker id="m" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 z" fill="#14213D"/></marker>
      <marker id="g" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 z" fill="#1B6B45"/></marker></defs>
    <path d="M44,95 L44,40 L108,40" stroke="#14213D" stroke-width="1.5" fill="none" marker-end="url(#m)"/>
    <path d="M44,95 L44,150 L108,150" stroke="#14213D" stroke-width="1.5" fill="none" marker-end="url(#m)"/>
    <path d="M262,40 L330,40 L330,95 L378,95" stroke="#14213D" stroke-width="1.5" fill="none" stroke-dasharray="5 4" marker-end="url(#m)"/>
    <path d="M262,150 L330,150 L330,95" stroke="#14213D" stroke-width="1.5" fill="none" stroke-dasharray="5 4"/>
    <path d="M186,62 L186,82" stroke="#1B6B45" stroke-width="1.2" fill="none" marker-end="url(#g)"/>
    <path d="M186,128 L186,108" stroke="#1B6B45" stroke-width="1.2" fill="none" marker-end="url(#g)"/>
    <text x="10" y="99" class="lbl">task</text>
    <text x="268" y="24" class="lbl">only if they disagree</text>
  </svg>
  <div class="node" style="left:110px;top:18px">Preparer<small style="top:-20px">bookkeeper, blind</small></div>
  <div class="node" style="left:110px;top:128px">Reviewer<small>auditor, blind</small></div>
  <div class="node" style="left:380px;top:73px">Referee<small>cites the IRS text</small></div>
  <div class="tool" style="left:130px;top:84px">line_guidance()</div>
</div>"""
    return (f'<div class="box graph" style="left:456px;top:118px;width:620px;height:350px">'
            f'<h2>{html.escape(head)}</h2>{canvas}<ul>{items}</ul></div>')


def _arrow(x1, y1, x2, y2, label, color="#14213D", lx=None, ly=None):
    lx = lx if lx is not None else (x1 + x2) / 2 + 8
    ly = ly if ly is not None else (y1 + y2) / 2 - 8
    return (f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{color}" stroke-width="2" fill="none" marker-end="url(#pm)"/>'
            f'<text x="{lx}" y="{ly}" class="lbl">{html.escape(label)}</text>')


def build_html() -> str:
    b1 = "left:48px;top:118px;width:330px;height:210px"
    b3 = "left:1166px;top:118px;width:386px;height:210px"
    b4 = "left:456px;top:540px;width:620px;height:150px;"
    b5 = "left:1166px;top:360px;width:386px;height:240px"
    labels = {(a, b): l for a, b, l in ARROWS}
    arrows = "".join([
        _arrow(378, 222, 456, 222, labels[(1, 2)], lx=380, ly=210),
        _arrow(1076, 222, 1166, 222, labels[(2, 3)], lx=1088, ly=210),
        _arrow(1076, 420, 1166, 420, labels[(2, 5)], lx=1078, ly=408),
        _arrow(766, 540, 766, 468, labels[(4, 2)], color="#8A4B00", lx=778, ly=510),
    ])
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<div class="page">
  <h1>NinetyNinety <span>ledger in, drafted Form 990-EZ out. Built with Strands Agents on Google Gemini.</span></h1>
  <p class="sub">Two agents classify every bank row without seeing each other; a third rules only on disagreement; totals are arithmetic in Python, never model output.</p>
  <svg style="position:absolute;left:0;top:0;width:1600px;height:760px">
    <defs><marker id="pm" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto">
      <path d="M0,0 L9,4.5 L0,9 z" fill="#14213D"/></marker></defs>{arrows}</svg>
  {_box(0, "", b1)}
  {_graph_box()}
  {_box(2, "", b3)}
  {_box(3, "model", b4)}
  {_box(4, "", b5)}
</div></body></html>"""


def render(dest: Path) -> Path:
    from playwright.sync_api import sync_playwright
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    html_path = dest.with_suffix(".html")
    html_path.write_text(build_html(), encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
        page.goto(html_path.resolve().as_uri())
        page.wait_for_timeout(1200)  # web fonts
        page.screenshot(path=str(dest), clip={"x": 0, "y": 0, "width": W, "height": H})
        browser.close()
    return dest


if __name__ == "__main__":
    print(render(Path("docs/architecture.png")))
