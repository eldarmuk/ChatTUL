from typing import Literal, Any, TypeAlias

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
_get_ast = create_markdown_processor()

Token: TypeAlias = dict[str, Any]


class MarkdownSection:
    """
    Represents a section (an optional header with a content).

    `headings` is a list of header names representing nesting level.
    If empty, represents a top-level content without header.
    """

    headings: list[str]
    content: list[Token]

    def __init__(self, headings: list[str], content: list[Token]):
        self.headings = headings
        self.content = content

    def __str__(self):
        stringified = ""
        for lvl, h in enumerate(self.headings):
            stringified += "#" * (lvl + 1) + " " + h + "\n\n"

        stringified += self.content
        return stringified


def get_ast(document_content: str) -> list[Token]:
    ast, _ = _get_ast.parse()

    # NOTE: if this is tripped, it indicades a programmer error
    #
    assert not isinstance(ast, str), (
        "could not get AST of Markdown document, is renderer set to None?"
    )

    return ast


def split_by_sections(document_content: str) -> list[MarkdownSection]:
    ast: list[Token] = get_ast(document_content)

    content: list[Token] = []
    headings: list[Token] = []
    sections: list[MarkdownSection] = []

    def push_section(heading: Token | None = None):
        sections.append(
            MarkdownSection(
                [h["children"][0]["raw"] for h in headings],
                format.renderer.render_tokens(content, mistune.BlockState()),
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
