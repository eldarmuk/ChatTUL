from ..markdown import split_by_sections


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
    assert len(fragments[0].headings) == 1
    assert len(fragments[1].headings) == 2
    assert len(fragments[2].headings) == 2

    assert fragments[0].headings == ["Main section"]
    assert fragments[1].headings == ["Main section", "Inner section"]
    assert fragments[2].headings == ["Main section", "Outer section"]
