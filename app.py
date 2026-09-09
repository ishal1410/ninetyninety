"""NinetyNinety -- draft an IRS Form 990-EZ from a nonprofit's raw ledger.

Built with Strands Agents.

Front: the federal-document interface -- Public Sans (the typeface USWDS
commissioned for federal use) and IBM Plex Mono on a light ground, one federal
blue accent. The drafted form is a paper sheet in a tray, the adjudication
record runs full width beneath it.
"""
import html
import itertools
import json
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import streamlit as st

from ninetyninety.ledger import load_ledger
from ninetyninety.lines import EXPENSE_LINES, REVENUE_LINES, form_order, line_by_number
from ninetyninety.pdffill import download_form, fill_form
from ninetyninety.prepare import prepare_ledger, trace_rows
from ninetyninety.recorded import load_recorded_run

BASE = Path(__file__).parent
st.set_page_config(page_title="NinetyNinety", page_icon=str(BASE / "assets" / "favicon.png"),
                   layout="wide")


def esc(text) -> str:
    return html.escape(str(text))


def money(n: int) -> str:
    """Accountant's style: negatives in parentheses."""
    return f"({abs(n):,})" if n < 0 else f"{n:,}"


CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Public+Sans:wght@300;400;500;600;700;800;900&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

/* The typeface is the argument. Public Sans is the face the United States Web
   Design System commissioned for federal government use, so the tool that
   drafts a federal form is set in the federal typeface. */
:root{
  --paper:#FFFFFF; --ground:#F4F5F6; --ink:#1B1B1B; --muted:#565C65;
  --accent:#005EA2; --accent-dark:#00437A; --notice:#B50909;
  --rule:#DFE1E2; --control:#8D9297; --band:#EDEFF0; --tint:#F0F6FB;
  --ease:cubic-bezier(.2,0,0,1);
  --sans:'Public Sans',system-ui,sans-serif; --mono:'IBM Plex Mono',ui-monospace,monospace;
}
#MainMenu, footer, header[data-testid="stHeader"]{visibility:hidden;height:0}
::selection{background:#CBE1F2;color:var(--ink)}
::-moz-selection{background:#CBE1F2;color:var(--ink)}
input,textarea{caret-color:var(--accent)}
a{text-underline-offset:.18em;text-decoration-thickness:1px}
*{scrollbar-width:thin;scrollbar-color:var(--control) var(--ground)}
*::-webkit-scrollbar{width:11px;height:11px}
*::-webkit-scrollbar-track{background:var(--ground)}
*::-webkit-scrollbar-thumb{background:var(--control);border:3px solid var(--ground)}
*::-webkit-scrollbar-thumb:hover{background:var(--muted)}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
html{scroll-behavior:smooth}
*{box-sizing:border-box}
section[data-testid="stMain"]{background:var(--ground)}
.block-container{max-width:1320px;margin:0 auto;padding:0 2rem 5rem}
.mast,.mast *,.steps,.steps *,.shell,.shell *,.adj,.adj *,
.note,.note *,.graph,.graph *,.foot,.foot *,.lead,.lead *,h2.sec,h3.sub,
p.lede,p.hero-lede,p.proof{
  font-family:var(--sans)}
p.lede{font-size:.93rem;color:var(--ink);max-width:66ch;line-height:1.55;margin:0 0 .9rem}
.num,table.ledger td.amt,table.ledger td.n,.adj .line,.adj .who,.mast .omb{
  font-family:var(--mono);font-variant-numeric:tabular-nums;font-feature-settings:"tnum" 1}

/* Masthead: the page chrome is the form's own header block.
   #C9CDD2 and #4A5056 are masthead-local shades, not palette tokens: they read
   against the ink band, not against paper. --muted is measured for contrast on
   white and goes grey-on-black here; --rule is a near-white hairline that glares
   on ink. So the band gets its own secondary text and its own hairline.
   --control (#8D9297) is the one existing token that would clear AA here, at
   5.49:1, but the band is the loudest thing on the page and #C9CDD2 reads at
   10.85:1; that trade is worth one local shade.
   Used nowhere else; not promoted to :root. */
.mast{display:flex;align-items:baseline;gap:1.5rem;flex-wrap:wrap;
  padding:1.05rem 1.15rem .95rem;background:var(--ink)}
.mast .mark{font-weight:800;font-size:1.32rem;letter-spacing:-.022em;color:var(--paper);line-height:1}
.mast .doc{font-weight:700;font-size:.95rem;color:var(--paper);letter-spacing:-.01em}
.mast .sub{font-size:.86rem;color:#C9CDD2}
.mast .omb{margin-left:auto;font-size:.74rem;letter-spacing:.02em;color:#C9CDD2;
  text-transform:uppercase;border:1px solid #4A5056;background:transparent;padding:.3rem .55rem}

/* The strip: one row of a bank export, and where it lands. */
/* padding:0 drops Streamlit's own 20/16px heading padding, which is framework
   chrome rather than this page's rhythm; 40ch puts the headline on one line at
   desktop widths, which is where the fold budget came from. */
.lead h1{font-size:clamp(1.9rem,2.9vw,2.75rem);font-weight:800;letter-spacing:-.035em;
  line-height:1.02;color:var(--ink);margin:.9rem 0 .8rem;max-width:40ch;padding:0;
  text-wrap:balance}
p.hero-lede{font-size:1.3rem;line-height:1.45;color:var(--ink);max-width:52ch;margin:0 0 1.1rem}
.lands{display:grid;grid-template-columns:minmax(0,1fr) 3.5rem minmax(0,1.3fr);
  align-items:start;margin:0 0 1rem}
.lands .from,.lands .to{background:var(--paper);border:1px solid var(--ink);
  padding:.85rem 1rem .95rem}
.lands .to{border-left-width:3px}
.lands .who{display:block;font-size:.72rem;color:var(--muted);line-height:1.4;
  margin-bottom:.5rem}
.lands b{display:block;font-family:var(--mono);font-size:.86rem;font-weight:600;color:var(--ink)}
.lands .desc{display:block;font-size:.95rem;line-height:1.4;color:var(--ink);margin-top:.2rem}
.lands .from .amt{display:block;margin-top:.7rem;font-size:1.15rem;font-weight:600;
  text-align:right;color:var(--ink)}
.lands .rowamt{display:flex;justify-content:space-between;align-items:baseline;
  margin-top:.7rem;padding-top:.55rem;border-top:1px solid var(--rule)}
.lands .rowamt .who{margin:0}
.lands .rowamt .num{font-family:var(--mono);font-size:1.15rem;font-weight:600;color:var(--ink)}
.lands .rule{margin:.7rem 0 0;padding-top:.55rem;border-top:1px solid var(--rule);
  font-size:.82rem;line-height:1.5;color:var(--muted)}
.lands .arrow{align-self:center;height:1px;background:var(--ink);position:relative}
.lands .arrow::after{content:"";position:absolute;right:0;top:-4px;
  border-left:8px solid var(--ink);border-top:4px solid transparent;
  border-bottom:4px solid transparent}
p.proof{font-size:.95rem;line-height:1.6;color:var(--ink);max-width:70ch;margin:0}
p.proof b{font-weight:600}

/* Three regions, three rules. Hairlines are the form's own device and stay
   inside the form sheet; they do not divide the page. */
.zone{height:3px;background:var(--ink);margin:1.15rem 0 1rem}

h2.sec{font-size:1.42rem;font-weight:700;letter-spacing:-.022em;color:var(--ink);
  margin:1.05rem 0 .3rem;padding:0}
h3.sub{font-size:.98rem;font-weight:700;letter-spacing:-.008em;color:var(--ink);
  margin:2rem 0 .55rem;padding-bottom:.35rem;border-bottom:1px solid var(--rule)}

/* The drafted form: a paper sheet inside a tray. */
.shell{background:var(--paper);border:1px solid var(--rule);padding:6px}
.form{background:var(--paper);border:1px solid var(--ink);padding:1.5rem 1.6rem 1.3rem}
.form .head{display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;
  border-bottom:2px solid var(--ink);padding-bottom:.7rem}
.form h2{font-size:1.16rem;font-weight:800;color:var(--ink);margin:0;letter-spacing:-.015em}
.form .note-sub{font-size:.82rem;color:var(--muted);margin:.2rem 0 0;max-width:52ch;line-height:1.45}
.stamp{flex:none;border:2px solid var(--notice);color:var(--notice);font-weight:800;
  font-size:.68rem;letter-spacing:.08em;padding:.24rem .5rem;text-transform:uppercase}

table.ledger{width:100%;border-collapse:collapse;font-size:.93rem;margin-top:.2rem}
table.ledger td{padding:.4rem .3rem;border:none;vertical-align:baseline;color:var(--ink)}
table.ledger td.n{width:2.9rem;font-size:.82rem;color:var(--muted);text-align:right;padding-right:.7rem}
table.ledger td.lab{position:relative;overflow:hidden}
/* The dotted leader is the form's own device, drawn once per row. */
table.ledger td.lab span{background:var(--paper);padding-right:.4rem;position:relative;z-index:1}
table.ledger td.lab::after{content:"";position:absolute;left:0;right:0;bottom:.34em;
  border-bottom:1px dotted #B7BCC0;z-index:0}
table.ledger td.cnt{width:5.4rem;text-align:right;font-size:.76rem;color:var(--muted);white-space:nowrap}
table.ledger td.amt{width:8rem;text-align:right;font-size:.92rem}
table.ledger tr.part td{background:var(--band);font-weight:700;font-size:.76rem;
  letter-spacing:.09em;text-transform:uppercase;padding:.42rem .3rem}
table.ledger tr.part td.lab::after,table.ledger tr.total td.lab::after{display:none}
table.ledger tr.empty td,table.ledger tr.empty td.lab span{color:var(--muted)}
table.ledger tr.total td{font-weight:700;padding-top:.5rem}
table.ledger tr.total td.amt{border-top:1px solid var(--ink);
  box-shadow:inset 0 -3px 0 -1px var(--paper),inset 0 -4px 0 -1px var(--ink)}

/* Adjudication record: the part no other entry has, so it gets the treatment. */
.adj{border:1px solid var(--rule);background:var(--paper);margin:0 0 .8rem}
.adj .row{display:flex;gap:.6rem;align-items:baseline;padding:.6rem .8rem;
  border-bottom:1px solid var(--rule);background:var(--band)}
.adj .row b{font-family:var(--mono);font-size:.78rem;font-weight:600;color:var(--muted);flex:none}
.adj .row span{font-size:.88rem;color:var(--ink);font-weight:600}
.adj .cols{display:grid;grid-template-columns:repeat(3,1fr)}
.adj .col{padding:.7rem .8rem .8rem;border-right:1px solid var(--rule)}
.adj .col:last-child{border-right:none}
.adj .who{display:block;font-size:.7rem;letter-spacing:.06em;text-transform:uppercase;
  color:var(--muted);margin-bottom:.28rem}
.adj .line{font-size:1.02rem;font-weight:600;color:var(--ink)}
.adj .rule{display:block;margin-top:.35rem;font-size:.79rem;line-height:1.45;color:var(--muted)}
.adj .col.win{background:var(--tint);box-shadow:inset 0 2px 0 var(--accent)}
.adj .col.win .line,.adj .col.win .who{color:var(--accent)}
.adj .col.out .line{color:var(--muted);text-decoration:line-through;text-decoration-thickness:1px}
.adj .verdict{padding:.5rem .8rem;border-top:1px solid var(--rule);font-size:.82rem;
  color:var(--ink);display:flex;gap:.55rem;align-items:center}
.adj .verdict em{font-style:normal;font-family:var(--mono);font-weight:600;color:var(--notice);
  border:1px solid var(--notice);padding:.1rem .35rem;font-size:.68rem;letter-spacing:.06em;
  text-transform:uppercase}

/* Provenance and flag notes */
.note{border-left:1px solid var(--accent);background:var(--paper);padding:.55rem .9rem;
  margin:0 0 .55rem;font-size:.87rem;line-height:1.5;color:var(--ink)}
.note.bad{border-left-color:var(--notice)}
.note .who{color:var(--muted);font-size:.79rem}
.note .pick{font-family:var(--mono);color:var(--accent);font-weight:600}
.note.bad .pick{color:var(--notice)}

/* The explainer band: how the graph reaches each line, in three columns.
   Three columns, matched to STEPS. Below 1100px they stack: at 768px three
   columns leave about 23 characters a line, which is a column of rubble. */
.steps{display:grid;grid-template-columns:repeat(3,1fr)}
.step{padding:0 1.6rem;border-right:1px solid var(--rule)}
.step:first-child{padding-left:0}
.step:last-child{border-right:none;padding-right:0}
.step h4{margin:0 0 .4rem;font-size:1rem;font-weight:700;color:var(--ink);letter-spacing:-.01em}
.step p{font-size:.88rem;color:var(--muted);line-height:1.55;margin:0}

/* The graph that ran */
.graph{border:1px solid var(--rule);background:var(--paper);padding:.9rem;overflow-x:auto}
.graph svg{width:100%;max-width:520px;min-width:430px;height:auto;display:block;margin:0 auto}
.graph .node{fill:var(--paper);stroke:var(--control);stroke-width:1}
.graph .node.hot{stroke:var(--accent);stroke-width:1.5}
.graph .lbl{font-family:var(--sans);font-size:14px;font-weight:700;fill:var(--ink)}
.graph .ms{font-family:var(--mono);font-size:11.5px;fill:var(--muted)}
.graph .edge{stroke:var(--control);stroke-width:1.2;fill:none}
.graph .edge.hot{stroke:var(--accent)}
.graph .edge.cond{stroke-dasharray:4 4}

/* Loading: a form shaped skeleton, not a spinner */
.skel .bar{height:13px;margin:.62rem 0;
  background:linear-gradient(90deg,var(--band) 0%,#E2E5E7 45%,var(--band) 90%);
  background-size:220% 100%;animation:shimmer 1.5s var(--ease) infinite}
@keyframes shimmer{to{background-position:-120% 0}}

/* The one authored moment: the sheet posts itself, top to bottom, on arrival.
   Exponential ease-out from an already-visible default, so nothing is hidden
   if the animation never runs. */
@media (prefers-reduced-motion: no-preference){
  table.ledger tr{animation:post .5s cubic-bezier(.16,1,.3,1) backwards;
    animation-delay:calc(var(--i,0) * 22ms)}
  @keyframes post{from{opacity:0;transform:translateY(-5px)}}
}

/* Footer */
.foot{border-top:1px solid var(--rule);margin-top:3.5rem;padding:1.1rem 0 .4rem;
  display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap;
  color:var(--muted);font-size:.82rem}
.foot a{color:var(--accent);text-decoration:none}
.foot a:hover{text-decoration:underline}

/* Streamlit controls, brought into the document language */
div.stButton>button{border-radius:2px;font-weight:600;font-size:.9rem;padding:.55rem 1.15rem;
  transition:background .2s var(--ease),transform .2s var(--ease),border-color .2s var(--ease)}
div.stButton>button[kind="primary"]{background:var(--accent);border:1px solid var(--accent);color:#fff}
div.stButton>button[kind="primary"]:hover,div.stButton>button[kind="primary"]:focus{
  background:var(--accent-dark);border-color:var(--accent-dark);color:#fff}
div.stButton>button[kind="secondary"]{background:var(--paper);border:1px solid var(--control);color:var(--ink)}
div.stButton>button[kind="secondary"]:hover{border-color:var(--ink);color:var(--ink)}
div.stButton>button:active{transform:translateY(1px)}
div.stButton>button:disabled{background:var(--band);border-color:var(--rule);
  color:var(--control);cursor:not-allowed}
div.stButton>button:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
[data-testid="stTextInput"] input{border-radius:2px;border:1px solid var(--control);
  background:var(--paper);color:var(--ink);font-family:var(--mono);font-size:.9rem}
[data-testid="stFileUploaderDropzone"]{border-radius:2px;border:1px solid var(--control);
  background:var(--paper);padding:.65rem .9rem;min-height:0}
/* the uploader ships its own "200MB per file" hint, carrying a middle dot this project does not use */
[data-testid="stFileUploaderDropzoneInstructions"] span:not([data-testid]){display:none}
[data-testid="stFileUploaderDropzoneInstructions"]{padding:0}
[data-testid="stFileUploader"] section{padding:0}
[data-testid="stWidgetLabel"] p{font-size:.82rem;font-weight:600;color:var(--ink)}
[data-testid="stExpander"] details{border:1px solid var(--rule);border-radius:2px;background:var(--paper)}

@media (prefers-reduced-motion: reduce){
  .skel .bar{animation:none}
  div.stButton>button{transition:none}}
@media (max-width:1100px){
  [data-testid="stHorizontalBlock"]{flex-wrap:wrap}
  [data-testid="stHorizontalBlock"]>[data-testid="stColumn"]{min-width:100%;flex:1 1 100%}
  .steps{grid-template-columns:1fr}
  .step{border-right:none;border-bottom:1px solid var(--rule);padding:.9rem 0}
  .step:last-child{border-bottom:none}}
@media (max-width:600px){
  .block-container{padding:0 1rem 4rem}
  .mast .omb{margin-left:0}
  .adj .cols{grid-template-columns:1fr}
  .adj .col{border-right:none;border-bottom:1px solid var(--rule)}
  table.ledger td.cnt{display:none}
  table.ledger td.amt{width:6rem}
  table.ledger td.n{width:2.3rem}
  table.ledger{font-size:.88rem}
  .lands{grid-template-columns:1fr}
  .lands .arrow{display:none}
  .lands .to{border-left-width:1px;border-top-width:3px}
  .steps{grid-template-columns:1fr}
  .step{border-right:none;border-bottom:1px solid var(--rule);padding:.9rem 0}
  .step:last-child{border-bottom:none}
  p.hero-lede{font-size:1.1rem}
  .form{padding:1.1rem 1rem 1rem}}
</style>"""
st.markdown(CSS, unsafe_allow_html=True)

report = None
report_path = BASE / "results" / "validation.json"
if report_path.exists():
    report = json.loads(report_path.read_text(encoding="utf-8"))

# Same idiom as report above: the hosted app must still boot if the recorded
# run is absent, it just loses the strip.
recorded_rows = None
demo_run_path = BASE / "results" / "demo_run.json"
if demo_run_path.exists():
    recorded_rows = json.loads(demo_run_path.read_text(encoding="utf-8"))["lines"]


def masthead() -> str:
    """The page chrome is the form's own header block."""
    return ('<div class="mast">'
            '<span class="mark">NinetyNinety</span>'
            '<span class="doc">Form 990-EZ</span>'
            '<span class="sub">Return of Organization Exempt From Income Tax, Part I</span>'
            '<span class="omb">OMB No. 1545-0047</span>'
            '</div>')


STEPS = (
    ("Two agents read every row, blind to each other",
     "Preparer and Reviewer are parallel entry nodes of one Strands graph. Each quotes the "
     "IRS instruction it relied on, and Python checks that quote word by word against the "
     "real text."),
    ("A referee settles only the rows they read differently",
     "A conditional edge fires on disagreement. The Referee may pick one of the two disputed "
     "lines and nothing else, and its reason is grounded against the IRS text too."),
    ("Python adds up, never the model",
     "Lines 9, 17 and 18 are computed from the classified rows by the same module that "
     "rebuilt the returns above from their own line items."),
)


def proof() -> str:
    """The validation numbers, stated at the width they were measured: line by
    line, against the returns actually checked, never the whole return."""
    def got(kind: str, field: str, fallback: str) -> str:
        return f"{report[kind][field]:,}" if report else fallback
    m9, c9 = got("matched", "line9", "3,632"), got("checked", "line9", "3,632")
    m17, c17 = got("matched", "line17", "3,617"), got("checked", "line17", "3,618")
    m18, c18 = got("matched", "line18", "3,619"), got("checked", "line18", "3,621")
    return (f'<p class="proof">Line 9 rebuilt exactly in <b class="num">{m9}</b> of '
            f'<b class="num">{c9}</b> returns checked from the IRS e-file corpus. '
            f'Line 17: <b class="num">{m17}</b> of <b class="num">{c17}</b>. '
            f'Line 18: <b class="num">{m18}</b> of <b class="num">{c18}</b>. '
            f'The misses are returns whose own stated totals disagree with their '
            f'own line items.</p>')


def hero_row() -> tuple[str, dict] | None:
    """The first classified row of the recorded run, in form order. Real output
    from a real Gemini run: description, amount and the rule the model quoted,
    all verbatim."""
    if not recorded_rows:
        return None
    for number in sorted(recorded_rows, key=form_order):
        transactions = recorded_rows[number]["transactions"]
        if transactions:
            return number, transactions[0]
    return None


def hero() -> str:
    """The page's one loud element: a line of a bank export becoming the form
    line it lands on, with the instruction that put it there."""
    row, strip = hero_row(), ""
    if row is not None:
        number, tx = row
        # The row's own amount only. The line's total belongs to the drafted
        # form; printing it here would read as this row's figure.
        strip = f"""<div class="lands">
  <div class="from">
    <span class="who">one row of a bank export</span>
    <b>{esc(tx["date"])}</b>
    <span class="desc">{esc(tx["description"])}</span>
    <span class="amt num">{money(tx["amount"])}</span>
  </div>
  <div class="arrow" aria-hidden="true"></div>
  <div class="to">
    <span class="who">the line, and the instruction that put it there</span>
    <b class="num">Line {esc(number)}</b>
    <span class="desc">{esc(line_by_number(number).label)}</span>
    <span class="rowamt"><span class="who">this row</span>
      <span class="num">{money(tx["amount"])}</span></span>
    <p class="rule">{esc(tx["rule"])}</p>
  </div>
</div>"""
    return f"""<div class="lead">
  <h1>A bank export goes in. This comes back.</h1>
  <p class="hero-lede">Every figure on the drafted form cites the transactions behind it
  and the sentence of the IRS instructions that put them there. It is a draft for an
  officer to review and sign, never a filing.</p>
  {strip}
  {proof()}
</div>"""


def explainer() -> str:
    """Shown until a draft exists: how the graph reaches each line."""
    steps = "".join(f'<div class="step"><h4>{h}</h4><p>{p}</p></div>' for h, p in STEPS)
    return f'<div class="steps">{steps}</div>'


ZONE = '<div class="zone"></div>'

FOOTER = ('<div class="foot">'
          '<span>Built with Strands Agents for the AWS Agents for Humans hackathon. '
          'Draft output only; an officer must review and sign.</span>'
          '<span><a href="https://github.com/ishal1410/ninetyninety">GitHub, MIT license</a></span>'
          '</div>')


def adjudication(item: dict) -> str:
    """One disputed row as a three column record. The column that reached the
    form is marked, the others are struck through."""
    used = item["used"]

    def col(who: str, line, rule) -> str:
        if line is None:
            return (f'<div class="col"><span class="who">{who}</span>'
                    '<span class="line">did not rule</span>'
                    '<span class="rule">The Preparer\u2019s line stands.</span></div>')
        state = "win" if line == used else "out"
        return (f'<div class="col {state}"><span class="who">{who}</span>'
                f'<span class="line">Line {esc(line)}</span>'
                f'<span class="rule">{esc(rule)}</span></div>')

    return ('<div class="adj">'
            f'<div class="row"><b>Row {item["source_row"]}</b>'
            f'<span>{esc(item["description"])}</span></div><div class="cols">'
            + col("Preparer", item["preparer"], item["preparer_rule"])
            + col("Reviewer", item["reviewer"], item["reviewer_rule"])
            + col("Referee", item["referee"], item["referee_reason"])
            + '</div><div class="verdict"><em>On the form</em>'
            f'<span>Line {esc(used)}</span></div></div>')


def graph_svg(trace: list[dict] | None) -> str:
    runs = [t for t in (trace or []) if not t.get("error")]

    def mean_ms(node):
        vals = [t["node_ms"].get(node) for t in runs if t.get("node_ms", {}).get(node) is not None]
        return round(sum(vals) / len(vals)) if vals else None

    referee_runs = sum(1 for t in runs if t.get("referee_ran"))
    tools = sum(t.get("tool_calls", 0) for t in runs)
    model_calls = sum(sum(t.get("model_calls", {}).values()) for t in runs)
    hot = bool(runs) and referee_runs > 0

    def box(name, x, y, sub, is_hot=True):
        return (f'<rect class="node{" hot" if is_hot else ""}" x="{x}" y="{y}" width="160" height="50" rx="1"/>'
                f'<text class="lbl" x="{x + 12}" y="{y + 21}">{name}</text>'
                f'<text class="ms" x="{x + 12}" y="{y + 39}">{sub}</text>')

    if runs:
        task = [f'{len(runs)} batches', f'{tools} tool calls']
        if model_calls:
            task.append(f'{model_calls} model calls, counted by Strands hooks')
        prep = f"{mean_ms('preparer'):,} ms mean" if mean_ms("preparer") else "did not run"
        rev = f"{mean_ms('reviewer'):,} ms mean" if mean_ms("reviewer") else "did not run"
        ref = f"ran {referee_runs} of {len(runs)} batches"
    else:
        task = ["12 rows per batch", "same task to both"]
        prep, rev, ref = "quotes an IRS rule", "never sees Preparer", "quotes the IRS text"
    svg = ['<svg viewBox="0 0 520 230" role="img" aria-label="Strands agent graph">',
           '<text class="lbl" x="6" y="112">Batch task</text>',
           f'<text class="ms" x="6" y="132">{task[0]}</text>',
           f'<text class="ms" x="6" y="150">{task[1]}</text>',
           f'<text class="ms" x="6" y="168">{task[2]}</text>' if len(task) > 2 else '',
           '<path class="edge hot" d="M112 120 C 130 120, 130 70, 150 70"/>',
           '<path class="edge hot" d="M112 120 C 130 120, 130 170, 150 170"/>',
           f'<path class="edge cond{" hot" if hot else ""}" d="M310 70 C 330 70, 330 120, 348 120"/>',
           f'<path class="edge cond{" hot" if hot else ""}" d="M310 170 C 330 170, 330 120, 348 120"/>',
           box("Preparer", 150, 45, prep), box("Reviewer", 150, 145, rev), box("Referee", 348, 95, ref, is_hot=hot),
           '<text class="ms" x="150" y="218">Dashed edges: only when they disagree.</text>',
           '</svg>']
    return '<div class="graph">' + "".join(svg) + "</div>"


pad_l, body, pad_r = st.columns([1, 12, 1])
with body:
    # Inside body, not above it: filled solid, a full-container masthead would
    # overhang the 12/14 content column by about 95px on each side.
    st.markdown(masthead() + hero() + ZONE, unsafe_allow_html=True)
    st.markdown('<h2 class="sec" id="draft-a-return">Draft a return</h2>'
                '<p class="lede">Upload a CSV with date, description and amount, or use the '
                'synthetic demo ledger. The agents run live; a 54-row ledger takes a few '
                'minutes on the free tier.</p>', unsafe_allow_html=True)
    c1, c2 = st.columns([3, 2])
    with c1:
        uploaded = st.file_uploader("Transaction ledger as CSV with date, description, amount", type="csv")
        use_demo = st.checkbox("Use the synthetic demo ledger instead", value=uploaded is None)
    with c2:
        # side by side, so the control strip's height is the uploader's, not
        # two stacked fields pushing the document out of the first viewport
        o1, o2 = st.columns([3, 2])
        org_name = o1.text_input("Organization name for the PDF", "DEMO COMMUNITY ORG")
        ein = o2.text_input("EIN for the PDF", "00-0000000")
    b1, b2 = st.columns([1, 2])
    go = b1.button("Draft a return", type="primary")
    replay = b2.button("Replay the recorded run (no model calls)",
                       help="Shows the draft recorded on 2026-09-08 from the demo ledger through Google Gemini. "
                            "Same code path, no quota used. Use it if the free tier for the day is spent.")
    st.markdown(ZONE, unsafe_allow_html=True)

    MAX_ROWS = 60  # the hosted demo shares one free-tier Gemini project

    def start_job(transactions, skipped):
        """Run the graph on a worker thread so a widget rerun (Enter in a text
        box, a click) cannot kill the run; the next script run resumes it."""
        job = {"done": (0, 1), "form": None, "error": None,
               "loaded": len(transactions), "skipped": skipped}

        def work():
            try:
                job["form"] = prepare_ledger(
                    transactions, max_rows=MAX_ROWS, exclusive=True,
                    progress=lambda done, total: job.__setitem__("done", (done, total)))
            except Exception as error:  # noqa: BLE001 - shown to the user below
                job["error"] = error
        job["thread"] = threading.Thread(target=work, daemon=True)
        job["thread"].start()
        st.session_state["job"] = job
        return job

    job = st.session_state.get("job")
    form, recorded, loaded, skipped = None, False, 0, []
    if (go or replay) and job is None:
        st.session_state.pop("draft", None)  # never show a stale draft under a new run
        with tempfile.TemporaryDirectory(prefix="ninetyninety-") as tmp:
            path = BASE / "fixtures" / "demo_ledger.csv"
            if go and uploaded is not None and not use_demo:
                path = Path(tmp) / "ledger.csv"
                path.write_bytes(uploaded.getvalue())
            try:
                transactions = load_ledger(path, skipped)
            except ValueError as error:
                st.error(f"Could not read the ledger: {error}")
                st.stop()
        if not transactions:
            st.error("No readable rows in the ledger: every row needs a description and an amount.")
            st.stop()
        if replay:
            form, recorded, loaded = load_recorded_run(BASE / "results" / "demo_run.json"), True, len(transactions)
        else:
            job = start_job(transactions, skipped)
    if job is not None:
        bar = st.progress(0.0, text="Preparer and Reviewer are reading the ledger in parallel")
        skeleton = st.empty()
        skeleton.markdown('<div class="shell"><div class="form skel">'
                          + "".join(f'<div class="bar" style="width:{w}%"></div>' for w in (38, 82, 74, 88, 61, 79, 45, 84, 70))
                          + '</div></div>', unsafe_allow_html=True)
        while job["thread"].is_alive():
            done, total = job["done"]
            if done:
                bar.progress(done / total, text=f"Batch {done} of {total} through the Strands graph")
            job["thread"].join(0.5)
        st.session_state.pop("job", None)
        skeleton.empty()
        bar.empty()
        if job["error"] is not None:
            st.error(f"Could not complete the draft: {job['error']}")
            st.stop()
        form, loaded, skipped = job["form"], job["loaded"], job["skipped"]
        exhausted = sum(t.get("rows", 0) for t in form.trace if "exhausted" in str(t.get("error", "")))
        if exhausted:
            st.warning(f"{exhausted} rows were not classified: the free-tier quota for today is spent. "
                       "Use the replay button above to see the recorded run.")
    if form is not None:
        pdf_bytes, pdf_error = None, None
        try:
            with tempfile.TemporaryDirectory(prefix="ninetyninety-") as tmp:
                pdf = fill_form(form, download_form(BASE / "data" / "f990ez.pdf"),
                                Path(tmp) / "draft.pdf", org_name, ein)
                pdf_bytes = pdf.read_bytes()
        except Exception as error:  # noqa: BLE001
            pdf_error = str(error)
        # Kept across reruns: the download button reruns the script and st.button
        # is False on that rerun, so without this the whole draft would vanish.
        st.session_state["draft"] = {"form": form, "skipped": skipped, "loaded": loaded,
                                     "pdf": pdf_bytes, "pdf_error": pdf_error, "recorded": recorded}

    draft = st.session_state.get("draft")
    if not draft:
        st.markdown(explainer(), unsafe_allow_html=True)
    if draft:
        form, skipped = draft["form"], draft["skipped"]
        if draft.get("recorded"):
            st.caption("Recorded on 2026-09-08 through Google Gemini; live runs use the same code.")
        st.markdown(
            f'<p class="lede" style="margin-top:.6rem">Read {draft["loaded"]} transactions'
            + (f", skipped {len(skipped)} with unreadable amounts." if skipped else ".") + "</p>",
            unsafe_allow_html=True)
        left, right = st.columns([3, 2], gap="large")

        with left:
            rows = ['<table class="ledger">']
            order = itertools.count()

            def row(html: str) -> None:
                """Each row carries its stagger index for the posting animation."""
                rows.append(html.replace("<tr", f'<tr style="--i:{next(order)}"', 1))

            for part, lines, total_key, total_label in (
                    ("Revenue", REVENUE_LINES, "line9", "Total revenue"),
                    ("Expenses", EXPENSE_LINES, "line17", "Total expenses")):
                row(f'<tr class="part"><td class="n"></td><td class="lab">{part}</td>'
                    f'<td class="cnt"></td><td class="amt"></td></tr>')
                for line in lines:
                    result = form.lines.get(line.number)
                    if result is None:
                        row(f'<tr class="empty"><td class="n">{line.number}</td>'
                            f'<td class="lab"><span>{esc(line.label)}</span></td>'
                            f'<td class="cnt"></td><td class="amt"></td></tr>')
                    else:
                        n = len(result.transactions)
                        row(f'<tr><td class="n">{line.number}</td>'
                            f'<td class="lab"><span>{esc(line.label)}</span></td>'
                            f'<td class="cnt">{n} row{"s" if n != 1 else ""}</td>'
                            f'<td class="amt">{money(result.amount)}</td></tr>')
                row(f'<tr class="total"><td class="n">{total_key[4:]}</td>'
                    f'<td class="lab">{total_label}</td><td class="cnt"></td>'
                    f'<td class="amt">{money(form.totals[total_key])}</td></tr>')
            row(f'<tr class="total"><td class="n">18</td>'
                f'<td class="lab">Excess or (deficit) for the year</td><td class="cnt"></td>'
                f'<td class="amt">{money(form.totals["line18"])}</td></tr>')
            rows.append("</table>")
            st.markdown(
                '<div class="shell"><div class="form"><div class="head"><div>'
                '<h2>Part I. Revenue, Expenses, and Changes in Net Assets</h2>'
                '<p class="note-sub">Totals are computed in Python from the classified rows. '
                'The model never does arithmetic.</p></div>'
                '<span class="stamp">Draft, not a filing</span></div>'
                + "".join(rows) + "</div></div>",
                unsafe_allow_html=True)

            if draft["pdf"] is not None:
                st.download_button("Download the PDF, marked DRAFT",
                                   draft["pdf"], file_name="990-EZ-DRAFT.pdf",
                                   mime="application/pdf")
            else:
                st.info(f"PDF not produced: {draft['pdf_error']}")

            st.markdown('<h3 class="sub">Where each line came from</h3>', unsafe_allow_html=True)
            for number in sorted(form.lines, key=form_order):
                result = form.lines[number]
                n = len(result.transactions)
                with st.expander(f"Line {number}, {line_by_number(number).label}: "
                                 f'{money(result.amount)} from {n} row{"s" if n != 1 else ""}'):
                    for c in result.transactions:
                        st.markdown(
                            f'<div class="note"><span class="who">row {c["source_row"]}, {esc(c["date"])}</span>'
                            f' &nbsp;{esc(c["description"])} &nbsp;<span class="pick">{money(c["amount"])}</span>'
                            f'<br><span class="who">Rule:</span> {esc(c["rule"])}</div>',
                            unsafe_allow_html=True)

        with right:
            st.markdown(f'<h3 class="sub">Low confidence, {len(form.low_confidence)}</h3>',
                        unsafe_allow_html=True)
            for item in form.low_confidence:
                st.markdown(f'<div class="note"><b>row {item["source_row"]}</b> {esc(item["description"])} '
                            f'<span class="pick">line {item["line"]}</span><br><span class="who">{esc(item["note"])}</span></div>',
                            unsafe_allow_html=True)
            if form.ungrounded:
                st.markdown(f'<h3 class="sub">Rule not found in the IRS guidance, {len(form.ungrounded)}</h3>',
                            unsafe_allow_html=True)
                for item in form.ungrounded:
                    st.markdown(f'<div class="note bad"><b>row {item["source_row"]}</b> <span class="pick">line {item["line"]}</span>'
                                f'<br><span class="who">Quoted rule:</span> {esc(item["rule"][:160])}</div>',
                                unsafe_allow_html=True)
            if form.unreviewed:
                st.markdown(f'<h3 class="sub">Single opinion only, {len(form.unreviewed)}</h3>',
                            unsafe_allow_html=True)
                for item in form.unreviewed:
                    st.markdown(f'<div class="note"><b>row {item["source_row"]}</b> {esc(item["description"])} '
                                f'<span class="pick">line {item["line"]}</span><br><span class="who">{esc(item["note"])}</span></div>',
                                unsafe_allow_html=True)
            if form.unclassified:
                st.markdown(f'<h3 class="sub">Not classified, {len(form.unclassified)}</h3>',
                            unsafe_allow_html=True)
                for item in form.unclassified:
                    st.markdown(f'<div class="note bad"><b>row {item["source_row"]}</b> {esc(item["description"])} '
                                f'<span class="pick">{money(item["amount"])}</span><br><span class="who">{esc(item["error"])}</span></div>',
                                unsafe_allow_html=True)
            if skipped:
                st.markdown(f'<h3 class="sub">Rows with unreadable amounts, {len(skipped)}</h3>',
                            unsafe_allow_html=True)
                for item in skipped:
                    st.markdown(f'<div class="note bad"><b>row {item["source_row"]}</b> {esc(item["description"])}'
                                f'<br><span class="who">Amount as written:</span> {esc(item["amount_raw"])}</div>',
                                unsafe_allow_html=True)

            with st.expander(f"Full Strands trace, {len(form.trace)} graph runs"):
                st.dataframe(trace_rows(form.trace), width="stretch", hide_index=True)

        st.markdown('<h3 class="sub">The graph that ran</h3>', unsafe_allow_html=True)
        st.markdown(graph_svg(form.trace), unsafe_allow_html=True)

        st.markdown(f'<h3 class="sub">Adjudication record, {len(form.disagreements)} rows</h3>'
                    '<p class="lede">The Reviewer never sees the Preparer, so these are two '
                    'independent readings of the same row. The Referee runs only where they '
                    'differ, and its reason is checked against the IRS text like any other.</p>',
                    unsafe_allow_html=True)
        for item in form.disagreements:
            st.markdown(adjudication(item), unsafe_allow_html=True)
        if not form.disagreements:
            st.markdown('<div class="note">Preparer and Reviewer agreed on every row.</div>',
                        unsafe_allow_html=True)

st.markdown(FOOTER, unsafe_allow_html=True)
