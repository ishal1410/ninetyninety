"""The architecture diagram is a required deliverable; the FAQ says what it
must show. Check its content against that spec and against the code."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import diagram  # noqa: E402

TEXT = [" ".join(lines).lower() for _, lines in diagram.BOXES]  # index = FAQ box - 1


def test_five_boxes_in_the_faq_order():
    heads = [h.lower() for h, _ in diagram.BOXES]
    assert len(heads) == 5
    for want, head in zip(["user input", "strands agents", "tools", "model provider", "output"], heads):
        assert want in head


def test_agent_box_names_the_full_agentic_loop_the_faq_asks_for():
    for word in ("model", "tool", "reasoning", "response"):
        assert word in TEXT[1], word


def test_arrows_flow_input_to_graph_to_output_and_the_model_serves_the_graph():
    edges = {(a, b) for a, b, _ in diagram.ARROWS}
    assert (1, 2) in edges and (2, 5) in edges
    assert (3, 5) not in edges  # tools do not produce the output; the graph does
    assert (4, 2) in edges or (2, 4) in edges


def test_diagram_matches_the_code():
    from ninetyninety.prepare import prepare_ledger
    import inspect
    assert "batch of 12" in diagram.BOXES[1][0].lower()
    assert "batch_size: int = 12" in inspect.getsource(prepare_ledger)
    assert "3 attempts" in TEXT[3] and "gemini" in TEXT[3]
