import urllib
import re

import scrapy
from scrapy.http import Response
from lxml import html

from ..items import AdmissionEnItem

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
        if any(tr.getparent() is t.getparent() for t in thead) if thead else False:
            continue
        cells = [ _escape_pipe(_text(c)) for c in tr.xpath("./th|./td") ]
        if any(c != "" for c in cells):
            rows.append(cells)

    if not rows:
        return ""
    
    # TODO: handle colspan/rowspan

def element_to_markdown(el) -> str:
	# detect table
	if getattr(el, "tag", "") == "table":
		return table_to_markdown(el)

	# headings
	if re.match(r"h[1-6]", getattr(el, "tag", "")):
		level = int(el.tag[1])
		return ("#" * level) + " " + _text(el) + "\n\n"

	# paragraph
	if getattr(el, "tag", "") == "p":
		return _text(el) + "\n\n"

	# lists
	if getattr(el, "tag", "") == "ul":
		items = []
		for li in el.xpath("./li"):
			items.append("- " + _text(li))
		return "\n".join(items) + "\n\n"
	if getattr(el, "tag", "") == "ol":
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
		parts.append(element_to_markdown(child))
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
            self.logger.warn("missing <main id='content'>, skipping..")
            return None

        # extract the title of the page
        title = response.xpath("//head//title/text()").get()

        main_html = main_xpath.get()
        try:
            markdown = html_main_to_markdown(main_html)
        except Exception:
            markdown = main_html

        # pass it to the pipeline
        yield AdmissionEnItem(
            response.url, title if title is not None else response.url, markdown
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
