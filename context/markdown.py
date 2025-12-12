from typing import Literal, TypedDict, NotRequired, Any, TYPE_CHECKING, cast
from collections.abc import Callable

import mistune
from mistune.renderers.markdown import MarkdownRenderer

from langchain_text_splitters import MarkdownTextSplitter


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
    def table_token_to_matrix(
        self, token: Token, state: mistune.BlockState
    ) -> list[list[str]]:
        table: list[list[str]] = []

        # table cannot exist without rows (which are children of 'table' token)
        assert "children" in token
        rows: list[Token] = token["children"]

        # don't know if order is guaranteed
        table_head: Token = next(filter(lambda t: t["type"] == "table_head", rows))
        table_body: Token = next(filter(lambda t: t["type"] == "table_body", rows))

        if TYPE_CHECKING:
            # table_head nor table_body can exist without children cells
            assert "children" in table_head
            assert "children" in table_body

        table.append(
            [
                self.render_children(cast(dict[str, Any], table_cell), state)
                for table_cell in table_head["children"]
            ]
        )
        for table_row in table_body["children"]:
            if TYPE_CHECKING:
                assert "children" in table_row

            table.append(
                [
                    self.render_children(cast(dict[str, Any], table_cell), state)
                    for table_cell in table_row["children"]
                ]
            )

        return table

    def table(self, token: Token, state: mistune.BlockState):
        table = self.table_token_to_matrix(token, state)

        # The following is a valid Markdown table
        # |header1|header2|
        # |-|-|
        # |cell1|cell2|
        #
        header = "|" + "|".join(table[0]) + "|\n|" + "-|" * len(table[0])
        body = "".join(["|" + "|".join(row) + "|\n" for row in table[1:]])

        return header + "\n" + body

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

    def __str__(self) -> str:
        renderer = MarkdownChunkRenderer()
        stringified = ""
        for lvl, h in enumerate(self.headings):
            stringified += "#" * (lvl + 1) + " " + h + "\n\n"

        stringified += renderer.render_tokens(self.content, mistune.BlockState())
        return stringified

    def split_into_chunks(
        self,
        chunk_size: int,
        chunk_overlap: int,
        length_function: Callable[[str], int],
    ) -> list[str]:
        splitter = MarkdownTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=length_function,
        )

        return splitter.split_text(str(self))


def get_ast(markdown_content: str) -> list[Token]:
    ast, _ = _get_ast.parse(markdown_content)

    # NOTE: if this is tripped, it indicades a programmer error
    #
    assert not isinstance(ast, str), (
        "could not get AST of Markdown document, is renderer set to None?"
    )

    return ast


def extract_text(token: Token) -> list[str]:
    if token["type"] == "text":
        return [token["raw"]]
    if "children" not in token:
        return []

    res = []
    for t in token["children"]:
        res += extract_text(t)
    return res


def split_by_sections(document_content: str) -> list[MarkdownSection]:
    ast: list[Token] = get_ast(document_content)

    content: list[Token] = []
    headings: list[Token] = []
    sections: list[MarkdownSection] = []

    def push_section(heading: Token | None = None):
        sections.append(
            MarkdownSection(
                [" ".join(extract_text(h)) for h in headings],
                content[:],
            )
        )
        content.clear()

        while (
            heading is not None
            and len(headings) != 0
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
