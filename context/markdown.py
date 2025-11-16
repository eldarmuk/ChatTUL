from typing import Literal

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


format = create_markdown_processor(renderer=MarkdownRenderer)
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
            stringified += "#" * (lvl + 1) + h + "\n\n"

        stringified += self.content
        return stringified


def split_by_sections(content: str) -> list[MarkdownSection]:
    renderer = MarkdownRenderer()
    ast = get_ast(content)

    content = []
    headings = []
    sections = []

    def is_section_top_level():
        return len(headings) == 0

    def is_section_empty():
        return len(content) == 0

    def should_split_section(token):
        # provided the token is a heading
        # .. if the previous heading has higher or equal level
        # .. (with examption on top level section)
        # .. and the section content is not empty
        # .. the section should be split
        return (
            token.get("type") == "heading"
            and (is_section_top_level() or headings[-1]["level"] >= token["level"])
            and not is_section_empty()
        )

    for token in ast:
        if token.get("type") == "heading":
            if should_split_section(token):
                sections.append(
                    MarkdownSection(list(headings), renderer.render_tokens(content))
                )
                content = []
                if not is_section_top_level():
                    headings.pop()

            headings.append(token)
            continue

        content += [token]

    return sections
