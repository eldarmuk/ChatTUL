from ..markdown import split_by_sections, get_ast


def test_splitting_by_sections():
    fragments = split_by_sections(
        """
# Main section

This is content for the main section.

## Inner section

More content for the inner section.

## Outer section

This section should be nested in main but not outer
"""
    )

    assert len(fragments) == 3

    assert fragments[0].headings == ["Main section"]
    assert fragments[1].headings == ["Main section", "Inner section"]
    assert fragments[2].headings == ["Main section", "Outer section"]


def test_splitting_no_headings():
    fragments = split_by_sections("Hey, this document has no headings but one section")

    assert len(fragments) == 1
    assert len(fragments[0].headings) == 0


def test_splitting_top_level():
    fragments = split_by_sections(
        """
Generic text content precedes the main document title

# Document title

Content specific to the document
"""
    )

    assert len(fragments) == 2
    assert fragments[0].headings == []
    assert fragments[1].headings == ["Document title"]
    assert equal_markdown(
        str(fragments[1]),
        """
# Document title

Content specific to the document
""",
    )


def test_fragment_to_str():
    # WARN: this test is flaky
    fragments = split_by_sections(
        """
Generic text content

# Level 1 section one

Lorem ipsum, dolor sit amet

## Abstract

Some abstract content here

# Level 1 section two

Never gonna give you up

""".strip()
    )

    assert len(fragments) == 4
    assert equal_markdown(str(fragments[0]), """Generic text content""")
    assert equal_markdown(
        str(fragments[1]),
        """
# Level 1 section one

Lorem ipsum, dolor sit amet
""",
    )
    assert equal_markdown(
        str(fragments[2]),
        """
# Level 1 section one

## Abstract

Some abstract content here
""",
    )
    assert equal_markdown(
        str(fragments[3]),
        """
# Level 1 section two

Never gonna give you up
""",
    )


# TODO: test with actual fixture


def equal_markdown(content_a: str, content_b: str) -> bool:
    a_ast = [token for token in get_ast(content_a) if token.get("type") != "blank_line"]
    b_ast = [token for token in get_ast(content_b) if token.get("type") != "blank_line"]

    return a_ast == b_ast
