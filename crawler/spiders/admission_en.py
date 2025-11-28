import urllib
import re
from copy import deepcopy

import scrapy
from scrapy.http import Response
from lxml import html

from ..items import AdmissionEnItem

import logging

logger = logging.getLogger(__name__)


def _text(node):
    if node is None:
        return ""
    text = "".join(node.itertext()) if hasattr(node, "itertext") else str(node)
    return re.sub(r"\s+", " ", text).strip()


def _escape_pipe(text):
    if text is not None:
        return text.replace("|", "\\|")
    return ""


def table_to_markdown(table_el) -> str:
    rows = []
    thead = table_el.xpath(".//thead")
    if thead:
        for tr in thead[0].xpath(".//tr"):
            cells = [_escape_pipe(_text(c)) for c in tr.xpath("./th|./td")]
            if any(c != "" for c in cells):
                rows.append(cells)
    for tr in table_el.xpath(".//tr"):
        if thead and any(tr.getparent() is t.getparent() for t in thead):
            continue
        cells = [_escape_pipe(_text(c)) for c in tr.xpath("./th|./td")]
        if any(c != "" for c in cells):
            rows.append(cells)

    if not rows:
        return ""

    cols = max(len(r) for r in rows)
    for r in rows:
        while len(r) < cols:
            r.append("")

    use_header = bool(table_el.xpath(".//th")) or len(rows) > 1
    header = rows[0] if use_header else [""] * cols
    body = rows[1:] if use_header else rows

    col_widths = [0] * cols
    for r in [header] + body:
        for i, cell in enumerate(r):
            col_widths[i] = max(col_widths[i], len(cell))

    def mkrow(r):
        return (
            "| " + " | ".join((r[i].ljust(col_widths[i]) for i in range(cols))) + " |"
        )

    lines = []
    lines.append(mkrow(header))
    lines.append(
        "| " + " | ".join(("-" * max(3, col_widths[i]) for i in range(cols))) + " |"
    )
    for r in body:
        lines.append(mkrow(r))
    return "\n".join(lines) + "\n\n"


def expand_tabs_to_sections(container, _visited_panes=None):
    if _visited_panes is None:
        _visited_panes = set()

    # find tablist (try ul[role=tablist] then nav with tab buttons/links)
    tablist = container.xpath(
        './ul[@role="tablist"] | ./nav[.//button[@role="tab"] or .//a[@role="tab"]]'
    )
    if not tablist:
        tablist = container.xpath(
            './/ul[@role="tablist"] | .//nav[.//button[@role="tab"] or .//a[@role="tab"]]'
        )
    if not tablist:
        return container
    tablist = tablist[0]
    tab_buttons = tablist.xpath(".//button[@aria-controls] | .//a[@aria-controls]")
    if not tab_buttons:
        return container

    sections = []
    processed_panes = set()

    for button in tab_buttons:
        try:
            label = _text(button) or "Untitled Tab"
            pane_id = button.get("aria-controls")
            if not pane_id or pane_id in processed_panes or pane_id in _visited_panes:
                continue

            pane = container.xpath(f'.//*[@id="{pane_id}"]')
            if not pane:
                continue

            pane = pane[0]
            processed_panes.add(pane_id)
            section = html.Element("section")
            h3 = html.Element("h3")
            h3.text = label
            section.append(h3)

            nested_tablist = pane.xpath(
                './ul[@role="tablist"] | .//ul[@role="tablist"]'
            )
            if nested_tablist:
                expanded_pane = expand_tabs_to_sections(
                    pane, _visited_panes | {pane_id}
                )
                for child in expanded_pane.iterchildren():
                    if isinstance(child.tag, str):
                        section.append(deepcopy(child))
            else:
                for child in pane.iterchildren():
                    if isinstance(child.tag, str):
                        section.append(deepcopy(child))

            sections.append(section)
        except Exception as e:
            logger.warning(f"Error processing tab: {e}")
            continue

    if not sections:
        return container

    new_container = html.Element("div")
    new_container.set("data-expanded-tabs", "true")
    for section in sections:
        new_container.append(section)

    return new_container


def _element_to_markdown_inline(el) -> str:
    result = []

    if el.text:
        result.append(el.text)

    # Process children
    for child in el:
        if not isinstance(child.tag, str):
            if child.tail:
                result.append(child.tail)
            continue

        # Links
        if child.tag == "a":
            href = child.get("href") or ""
            text = (
                _element_to_markdown_inline(child)
                if len(child) > 0
                else (child.text or "")
            )
            text = re.sub(r"\s+", " ", text).strip()
            if href:
                result.append(f"[{text}]({href})")
            else:
                result.append(text)

        # Bold
        elif child.tag in ("strong", "b"):
            text = (
                _element_to_markdown_inline(child)
                if len(child) > 0
                else (child.text or "")
            )
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                result.append(f"**{text}**")

        # Italic
        elif child.tag in ("em", "i"):
            text = (
                _element_to_markdown_inline(child)
                if len(child) > 0
                else (child.text or "")
            )
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                result.append(f"*{text}*")

        # Line break
        elif child.tag == "br":
            result.append("  \n")  # Two spaces + newline = line break in markdown
            # TODO: Check if this works correctly in all cases

        # Span and other inline elements
        elif child.tag == "span":
            result.append(
                _element_to_markdown_inline(child)
                if len(child) > 0
                else (child.text or "")
            )

        # Fallback
        else:
            result.append(
                _element_to_markdown_inline(child)
                if len(child) > 0
                else (child.text or "")
            )

        if child.tail:
            result.append(child.tail)

    return "".join(result)


def element_to_markdown(el) -> str:
    # Images
    if el.tag == "img":
        alt = el.get("alt") or ""
        return f"{alt}\n" if alt else ""

    # Tab container
    if el.tag == "div":
        has_tablist = bool(el.xpath('.//nav | .//ul[@role="tablist"]'))
        has_content = bool(el.xpath('.//div[contains(@class,"tab-content")]'))

        has_tab_controls = bool(
            el.xpath(".//button[@aria-controls] | .//a[@aria-controls]")
        )

        # Only process if we have all three components
        if has_tablist and has_content and has_tab_controls:
            try:
                # Transform tabs into sections
                expanded = expand_tabs_to_sections(el)

                if expanded.get("data-expanded-tabs") == "true":
                    parts = []
                    for child in expanded.iterchildren():
                        if isinstance(child.tag, str):
                            parts.append(element_to_markdown(child))
                    return "".join(parts)
                else:
                    logger.debug(
                        "Tab expansion did not occur, processing as regular div"
                    )
            except Exception as e:
                logger.warning(
                    f"Error expanding tabs, falling back to regular processing: {e}"
                )

    # Container blocks: recurse into children (section/div/article)
    if el.tag in ("section", "div", "article"):
        parts = []
        for child in el.iterchildren():
            if not isinstance(child.tag, str):
                continue
            parts.append(element_to_markdown(child))
        return "".join(parts)

    # Line breaks
    if el.tag == "br":
        return "\n"

    # Table
    if el.tag == "table":
        return table_to_markdown(el) + "\n"

    # Headings
    if re.match(r"h[1-6]", el.tag):
        level = int(el.tag[1])
        text = _element_to_markdown_inline(el) if len(el) > 0 else (el.text or "")
        text = text.strip()
        if not text:
            return ""  # Skip empty headings
        return ("#" * level) + " " + text + "\n\n"

    # Paragraph
    if el.tag == "p":
        text = _element_to_markdown_inline(el) if len(el) > 0 else (el.text or "")
        text = text.strip()
        if not text:
            return ""
        return text + "\n\n"

    # Lists
    if el.tag == "ul":
        items = []
        for li in el.xpath("./li"):
            text = _element_to_markdown_inline(li) if len(li) > 0 else (li.text or "")
            text = text.strip()
            if text:
                items.append("- " + text)
        return "\n".join(items) + "\n\n" if items else ""

    if el.tag == "ol":
        items = []
        for i, li in enumerate(el.xpath("./li"), start=1):
            text = _element_to_markdown_inline(li) if len(li) > 0 else (li.text or "")
            text = text.strip()
            if text:
                items.append(f"{i}. " + text)
        return "\n".join(items) + "\n\n" if items else ""

    # Links
    if el.tag == "a":
        href = el.get("href") or ""
        text = _element_to_markdown_inline(el) if len(el) > 0 else (el.text or href)
        text = text.strip()
        if not text:
            return ""
        return f"[{text}]({href})\n" if href else text + "\n"

    # Inline formatting elements at block level
    if el.tag in ("span", "strong", "em", "b", "i"):
        text = _element_to_markdown_inline(el)
        return text + "\n" if text.strip() else ""

    # Fallback
    text = _text(el)
    return text + "\n" if text else ""


def html_main_to_markdown(main_html: str) -> str:
    try:
        frag = html.fromstring(main_html)
    except Exception as e:
        logger.error(f"Failed to parse HTML: {e}")
        return ""

    parts = []

    for child in frag.iterchildren():
        try:
            parts.append(element_to_markdown(child))
        except Exception as e:
            logger.warning(f"Skipping child <{child.tag}>: {e}")

    result = "".join(parts)
    # Clean up extra spaces and newlines
    result = re.sub(r"\n{3,}", "\n\n", result)
    result = re.sub(r" +\n", "\n", result)

    return result.strip() + "\n"


class AdmissionEnSpider(scrapy.Spider):
    name = "admission_en"
    allowed_domains = ["apply.p.lodz.pl"]
    start_urls = [
        "https://apply.p.lodz.pl/en/enrollment/enroll/fees-and-scholarships",
    ]

    def parse_text_response(self, response: Response):
        # page content is placed in <main id="content">
        main_xpath = response.xpath('//main[@id="content"]')
        if len(main_xpath) == 0:
            logger.warning("missing <main id='content'>, skipping..")
            return None

        # extract the title of the page
        title = response.xpath("//head//title/text()").get()

        main_html = main_xpath.get()
        try:
            markdown = html_main_to_markdown(main_html)
        except Exception:
            markdown = _text(html.fromstring(main_html))

        # pass it to the pipeline
        yield AdmissionEnItem(
            url=response.url,
            title=title if title is not None else response.url,
            content=markdown,
            # content_text=_text(html.fromstring(main_html)) # This is for plain text content, use it when the time comes :)
            # TODO: Add more fields, e.g., lang, content_markdown, timestamp to integrate into ChromaDB
        )

        # get all links
        for href in response.xpath("//a/@href").getall():
            # filter go-to links (#top-of-page etc)
            href = href.strip()
            if len(href) == 0 or href[0] == "#":
                continue

            href = urllib.parse.urljoin(response.url, href)

            # make sure we follow http(s) links
            url = urllib.parse.urlparse(href)
            if not url.scheme.startswith("http"):
                continue
            path = url.path.split("/")[1:]

            # make sure we stay on the english page
            # rekrutacja.p.lodz.pl = polish
            # apply.p.lodz.pl/en = english
            # apply.p.lodz.pl/ = broken, polish mixed with english
            # rekrutacja.p.lodz.pl/en = polish ??
            if len(path) == 0 or path[0] != "en":
                continue

            yield response.follow(href)

    def parse(self, response: Response):
        # check if we got a text response
        if isinstance(response, scrapy.http.TextResponse):
            yield from self.parse_text_response(response)
