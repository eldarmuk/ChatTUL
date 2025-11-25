import urllib
import re

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
            cells = [ _escape_pipe(_text(c)) for c in tr.xpath("./th|./td") ]
            if any(c != "" for c in cells):
                rows.append(cells)
    for tr in table_el.xpath(".//tr"):
        if thead and any(tr.getparent() is t.getparent() for t in thead):
            continue
        cells = [ _escape_pipe(_text(c)) for c in tr.xpath("./th|./td") ]
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
        return "| " + " | ".join((r[i].ljust(col_widths[i]) for i in range(cols))) + " |"

    lines = []
    lines.append(mkrow(header))
    lines.append("| " + " | ".join(("-" * max(3, col_widths[i]) for i in range(cols))) + " |")
    for r in body:
        lines.append(mkrow(r))
    return "\n".join(lines) + "\n\n"

def tabs_to_markdown(container) -> str:
    navs = container.xpath(".//nav")
    tab_contents = container.xpath(".//div[contains(@class,'tab-content')]")
    if not navs or not tab_contents:
        return ""
    nav = navs[0]
    tab_content = tab_contents[0]

    label_nodes = nav.xpath(".//a|.//button|.//li")
    labels = [ _text(n) for n in label_nodes if _text(n) ]

    panes = [c for c in tab_content.getchildren() if isinstance(c.tag, str)]
    out = []
    if labels and panes:
        n = min(len(labels), len(panes))
        for i in range(n):
            label = labels[i]
            pane = panes[i]
            out.append("### " + label + "\n\n")
            for child in pane.iterchildren():
                out.append(element_to_markdown(child))
    else:
        for pane in panes:
            for child in pane.iterchildren():
                out.append(element_to_markdown(child))
    return "\n".join(out) + "\n\n"

def expand_tabs_to_sections(container, _visited_panes=None):
    if _visited_panes is None:
        _visited_panes = set()

    # find tablist (try ul[role=tablist] then nav with tab buttons/links)
    tablist = container.xpath('.//ul[@role="tablist"]')
    if not tablist:
        tablist = container.xpath('.//nav[.//button[@role="tab"] or .//a[@role="tab"]]')
    if not tablist:
        return container
    tablist = tablist[0]

    # ensure tablist belongs to this container (avoid deep-nested ones)
    tablist_parent = tablist.getparent()
    depth = 0
    current = tablist_parent
    while current is not None and current != container:
        current = current.getparent()
        depth += 1
        if depth > 10:
            logger.warning("Tablist parent depth exceeded safety limit")
            return container

    tab_buttons = tablist.xpath('.//button[@aria-controls] | .//a[@aria-controls]')
    if not tab_buttons:
        logger.debug("No tab buttons found with aria-controls attribute")
        return container

    sections = []
    processed_panes_at_this_level = set()
    processed_count = 0

    for button in tab_buttons:
        try:
            label = _text(button) or "Untitled Tab"
            pane_id = button.get('aria-controls')
            if not pane_id or pane_id in processed_panes_at_this_level:
                continue

            _visited_panes.add(pane_id)
            escaped_id = pane_id.replace('"', '\\"')
            pane_nodes = container.xpath(f'.//*[@id="{escaped_id}"]')
            if not pane_nodes:
                logger.debug(f"No pane found for ID: {pane_id}")
                continue
            pane = pane_nodes[0]

            processed_panes_at_this_level.add(pane_id)

            section = html.Element('section')
            h3 = html.Element('h3')
            h3.text = label
            section.append(h3)

            # DFS: expand nested tablists first
            nested_tablist = pane.xpath('.//ul[@role="tablist"]')
            if nested_tablist:
                branch_visited = _visited_panes | {pane_id}
                try:
                    expanded_pane = expand_tabs_to_sections(pane, branch_visited)
                    for child in expanded_pane.iterchildren():
                        if isinstance(child.tag, str):
                            section.append(child)
                except Exception as e:
                    logger.warning(f"Error expanding nested tabs for pane {pane_id}: {e}")
                    for child in pane.iterchildren():
                        if isinstance(child.tag, str):
                            section.append(child)
            else:
                for child in pane.iterchildren():
                    if isinstance(child.tag, str):
                        section.append(child)

            sections.append(section)
            processed_count += 1

        except Exception as e:
            logger.warning(f"Error processing tab button: {e}")
            continue

    if processed_count == 0:
        logger.debug("No tabs were successfully processed")
        return container

    new_container = html.Element('div')
    new_container.set('data-expanded-tabs', 'true')
    for section in sections:
        new_container.append(section)

    return new_container

def element_to_markdown(el) -> str:
    # links
    if el.tag == "a":
        href = el.get("href") or ""
        text = _text(el) or href
        return f"[{text}]({href})" if href else text

    # images
    if el.tag == "img":
        src = el.get("src") or el.get("data-src") or ""
        alt = el.get("alt") or ""
        return f"![{alt}]({src})" if src else alt
    
    # tab container
    if el.tag == "div":
        has_tablist = bool(el.xpath('.//nav | .//ul[@role="tablist"]'))
        has_content = bool(el.xpath('.//div[contains(@class,"tab-content")]'))
        
        if has_tablist and has_content:
            expanded = expand_tabs_to_sections(el)
            parts = []
            for child in expanded.iterchildren():
                if isinstance(child.tag, str):
                    parts.append(element_to_markdown(child))
            return "".join(parts)

    # container blocks: recurse into children (section/div/article)
    if el.tag in ("section", "div", "article"):
        parts = []
        for child in el.iterchildren():
            if not isinstance(child.tag, str):
                continue
            parts.append(element_to_markdown(child))
        return "".join(parts)
    
    # inline formatting
    if el.tag in ("span", "strong", "em", "b", "i", "code"):
        return _text(el)

    # line breaks
    if el.tag == "br":
        return "\n"

    # table
    if el.tag == "table":
        return table_to_markdown(el)

    # headings
    if re.match(r"h[1-6]", el.tag):
        level = int(el.tag[1])
        return ("#" * level) + " " + _text(el) + "\n\n"

    # paragraph
    if el.tag == "p":
        return _text(el) + "\n\n"

    # lists
    if el.tag == "ul":
        items = []
        for li in el.xpath("./li"):
            items.append("- " + _text(li))
        return "\n".join(items) + "\n\n"
    if el.tag == "ol":
        items = []
        for i, li in enumerate(el.xpath("./li"), start=1):
            items.append(f"{i}. " + _text(li))
        return "\n".join(items) + "\n\n"

    # fallback
    return _text(el) + ("\n\n" if _text(el) else "")

def html_main_to_markdown(main_html: str) -> str:
    frag = html.fromstring(main_html)
    parts = []

    for child in frag.iterchildren():
        try:
            parts.append(element_to_markdown(child))
        except Exception as e:
            logger.warning(f"Skipping child <{child.tag}>: {e}")
    return "".join(parts).strip() + "\n"


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
            content=markdown
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
