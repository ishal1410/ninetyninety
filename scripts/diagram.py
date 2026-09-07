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
      "Loop per node: model -> tools -> reasoning -> response",
      "Tool = line_guidance; response = pydantic structured output",
      "Conditional edge to referee only when their lines differ"]),
    ("3  Tools & integrations",
     ["@tool line_guidance: IRS 990-EZ Part I instruction text",
      "pydantic BatchCalls / Verdicts = structured output",
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


# (from box, to box, label). Output comes from the graph; Bedrock serves the graph.
ARROWS = [(1, 2, ""), (2, 3, ""), (4, 2, "Bedrock serves every node"), (2, 5, "graph output")]


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

    def head(x, y, dx, dy):
        d.polygon([(x, y), (x - 14 * dx - 8 * dy, y - 14 * dy - 8 * dx),
                   (x - 14 * dx + 8 * dy, y - 14 * dy + 8 * dx)], fill=LINE)

    centres = {i + 1: ((x0 + x1) // 2, (y0 + y1) // 2, x0, y0, x1, y1)
               for i, (x0, y0, x1, y1) in enumerate(cols)}
    for a, b, label in ARROWS:
        ax, ay, ax0, ay0, ax1, ay1 = centres[a]
        bx, by, bx0, by0, bx1, by1 = centres[b]
        if ay == by:  # side by side: right edge of a -> left edge of b
            start, end, dx, dy = (ax1, ay - 60), (bx0, by - 60), 1, 0
        elif ay < by:  # a above b: bottom of a -> top of b
            x = ax1 - 120 if a == 2 and b == 5 else ax
            start, end, dx, dy = (x, ay1), (x, by0), 0, 1
        else:  # a below b: top of a -> bottom of b
            x = bx0 + 120 if b == 2 else ax
            start, end, dx, dy = (x, ay0), (x, by1), 0, -1
        d.line([start, end], fill=LINE, width=4)
        head(end[0], end[1], dx, dy)
        if label:
            d.text((start[0] + 12, (start[1] + end[1]) // 2 - 10), label, fill="#52606d", font=small)

    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest)
    return dest


if __name__ == "__main__":
    print(render(Path("docs/architecture.png")))
