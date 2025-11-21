from typing import Literal, Any

import mistune
from mistune.renderers.markdown import MarkdownRenderer


def create_markdown_processor(
    renderer: Literal["html", "ast"] | mistune.BaseRenderer | None = None,
) -> mistune.Markdown:
    """
    Create preconfigured `mistune.Markdown` instance.

    Refer to mistune documentation on `renderer` parameter.
    """
    return mistune.create_markdown(renderer=renderer, plugins=["table"])


format = create_markdown_processor(renderer=MarkdownRenderer())
get_ast = create_markdown_processor()


class MarkdownSection:
    """
    Represents a section (an optional header with a content).

    `headings` is a list of header names representing nesting level.
    If empty, represents a top-level content without header.
    """

    headings: list[str]
    content: str

    def __init__(self, headings: list[str], content: str):
        self.headings = headings
        self.content = content

    def __str__(self):
        stringified = ""
        for lvl, h in enumerate(self.headings):
            stringified += "#" * (lvl + 1) + " " + h + "\n\n"

        stringified += self.content
        return stringified


def split_by_sections(document_content: str) -> list[MarkdownSection]:
    renderer = MarkdownRenderer()

    ast: list[dict[str, Any]] | str = get_ast(document_content)
    if isinstance(ast, str):
        return [MarkdownSection([], ast)]

    content: list[dict[str, Any]] = []
    headings: list[dict[str, Any]] = []
    sections: list[MarkdownSection] = []

    def push_section(heading: dict[str, Any] | None = None):
        sections.append(
            MarkdownSection(
                [h["children"][0]["raw"] for h in headings],
                renderer.render_tokens(content, mistune.BlockState()),
            )
        )
        content.clear()

        if heading is not None:
            while (
                len(headings) != 0
                and headings[-1]["attrs"]["level"] >= heading["attrs"]["level"]
            ):
                headings.pop()

    for token in ast:
        token_type = token.get("type")
        if token_type == "blank_line":
            continue

        if token_type == "heading":
            if len(content) != 0:
                push_section(token)

            headings.append(token)
            continue

        content.append(token)

    if len(content) != 0:
        push_section()

    return sections
