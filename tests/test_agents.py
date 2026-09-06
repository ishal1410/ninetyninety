from ninetyninety.agents import line_reference, parse_classification


def test_parse_classification_reads_the_structured_reply():
    text = ("LINE: 13\n"
            "RULE: line 13 covers payments to non-employees\n"
            "WHY: Venmo to an individual instructor, not payroll\n"
            "CONFIDENCE: high")
    result = parse_classification(text, source_row=7)
    assert result.line_number == "13"
    assert result.source_row == 7
    assert result.confidence == "high"
    assert "non-employees" in result.rule


def test_parse_classification_rejects_a_line_not_on_the_form():
    assert parse_classification("LINE: 99\nRULE: x\nWHY: y\nCONFIDENCE: high",
                                source_row=1) is None


def test_parse_classification_rejects_unstructured_output():
    assert parse_classification("I think this is probably rent?",
                                source_row=1) is None


def test_parse_classification_defaults_missing_confidence_to_low():
    assert parse_classification("LINE: 1\nRULE: r\nWHY: w",
                                source_row=1).confidence == "low"


def test_line_reference_lists_every_line_with_guidance():
    reference = line_reference()
    assert "5c" in reference and "6d" in reference
    assert "independent contractors" in reference
