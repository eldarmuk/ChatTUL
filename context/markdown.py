from typing import Literal, TypedDict, NotRequired, Any

import mistune
from mistune.renderers.markdown import MarkdownRenderer

import tabulate


class Token(TypedDict):
    """
    Token/semantic element of Markdown.

    Types have been inferred by reading `mistune` code
    """

    type: str
    children: NotRequired[list["Token"]]
    raw: NotRequired[str]
    attrs: NotRequired[dict[str, Any]]
    style: NotRequired[str]


class MarkdownChunkRenderer(MarkdownRenderer):
    def table(self, token: Token, state: mistune.BlockState):
        table: list[list[str]] = []

        # table cannot exist without rows (which are children of 'table' token)
        assert "children" in token
        rows: list[Token] = token["children"]
        table_head: Token = next(filter(lambda t: t["type"] == "table_head", rows))
        table_body: Token = next(filter(lambda t: t["type"] == "table_body", rows))

        table.append(
            [
                self.render_children(table_cell, state)
                for table_cell in table_head["children"]
            ]
        )
        for table_row in table_body["children"]:
            table.append(
                [
                    self.render_children(table_cell, state)
                    for table_cell in table_row["children"]
                ]
            )

        return tabulate.tabulate(
            table,
            tablefmt="github",
            headers="firstrow",
        )

    def table_cell(self, token: Token, state: mistune.BlockState):
        return self.render_children(token, state)


def create_markdown_processor(
    renderer: Literal["html", "ast"] | mistune.BaseRenderer | None = None,
) -> mistune.Markdown:
    """
    Create preconfigured `mistune.Markdown` instance.

    Refer to mistune documentation on `renderer` parameter.
    """
    return mistune.create_markdown(renderer=renderer, plugins=["table"])


format = create_markdown_processor(renderer=MarkdownChunkRenderer())
_get_ast = create_markdown_processor()


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
