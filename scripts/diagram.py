"""Render docs/architecture.png: the five boxes the hackathon FAQ asks for.

    python scripts/diagram.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1600, 900
BG, INK, BOX, LINE, ACCENT = "#ffffff", "#1f2933", "#f5f7fa", "#9aa5b1", "#ff9900"

BOXES = [
    ("1  User input / interface",
     ["Volunteer treasurer uploads the bank ledger CSV",
      "Streamlit app (app.py) or CLI (cli.py)",
      "date, description, amount; whole dollars, +in / -out"]),
    ("2  Strands Agents graph (per batch of 12 rows)",
     ["GraphBuilder: preparer + reviewer as blind parallel entry nodes",
      "Each node: model -> line_guidance tool -> structured output",
      "Conditional edge to referee, only when their lines differ",
      "Python check: the quoted rule must be in the IRS text"]),
    ("3  Tools & integrations",
     ["@tool line_guidance: IRS 990-EZ Part I instruction text",
      "pydantic schemas BatchCalls / Verdicts for structured output",
      "IRS e-file XML corpus: 3,687 real returns check formmath"]),
    ("4  AWS services",
     ["Amazon Bedrock: Claude via Strands BedrockModel (one provider)",
      "Standard AWS credentials; Free-plan account, signup credit",
      "Throttle/5xx: advertised-delay backoff, 3 attempts, then surfaced"]),
    ("5  Output",
     ["Form 990-EZ Part I, every line citing rows + the IRS rule",
      "Totals (lines 9, 17, 18) computed in formmath.py, never by a model",
      "Disagreements, low confidence, unclassified rows all shown",
      "Filled IRS f990ez.pdf, DRAFT notice on every page"]),
]


def _font(size: int):
    for name in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render(dest: Path) -> Path:
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    title, body, small = _font(34), _font(21), _font(16)
    d.text((40, 28), "NinetyNinety: ledger -> Form 990-EZ draft, built with Strands Agents on Amazon Bedrock",
           fill=INK, font=title)
    d.text((40, 74), "Preparer and Reviewer never see each other; the Referee runs only on disagreement; "
                     "totals are arithmetic, not model output.", fill="#52606d", font=small)

    cols = [(40, 120, 480, 480), (560, 120, 1040, 480), (1120, 120, 1560, 480),
            (40, 560, 760, 860), (840, 560, 1560, 860)]
    for (x0, y0, x1, y1), (head, lines) in zip(cols, BOXES):
        d.rounded_rectangle((x0, y0, x1, y1), radius=14, fill=BOX, outline=LINE, width=2)
        d.rectangle((x0, y0, x0 + 8, y1), fill=ACCENT)
        d.text((x0 + 24, y0 + 16), head, fill=INK, font=body)
        y = y0 + 64
        for line in lines:
            d.text((x0 + 24, y), "- " + line, fill=INK, font=small)
            y += 30

    def arrow(a, b):
        d.line([a, b], fill=LINE, width=4)
        x, y = b
        d.polygon([(x, y), (x - 14, y - 8), (x - 14, y + 8)], fill=LINE)

    arrow((480, 300), (560, 300))
    arrow((1040, 300), (1120, 300))
    d.line([(800, 480), (800, 560)], fill=LINE, width=4)
    d.polygon([(800, 560), (792, 546), (808, 546)], fill=LINE)
    d.line([(1340, 480), (1340, 560)], fill=LINE, width=4)
    d.polygon([(1340, 560), (1332, 546), (1348, 546)], fill=LINE)
    d.text((820, 505), "Bedrock hosts the model behind every node", fill="#52606d", font=small)
    d.text((1180, 505), "Output of the graph", fill="#52606d", font=small)

    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest)
    return dest


if __name__ == "__main__":
    print(render(Path("docs/architecture.png")))
