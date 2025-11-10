import urllib

import scrapy
from scrapy.http import Response

from dataclasses import dataclass
from parsel.selector import SelectorList
from ..items import AdmissionEnItem


# UNUSED
@dataclass
class FnSTab:
    path: list[str]
    content: str


# UNUSED
def parse_FnS_tablist(response: Response, tablist: SelectorList) -> list[FnSTab]:
    tablist_buttons = tablist.xpath(".//button")
    tab_ids = tablist_buttons.xpath("./@aria-controls").getall()
    tab_titles = tablist_buttons.xpath("./text()").getall()

    tabs: list[FnSTab] = []

    for tab_id, tab_title in zip(tab_ids, tab_titles):
        tab_xpath = response.xpath(f'//*[@id="{tab_id}"]')

        if len(tab_xpath) == 0:
            continue

        subtablist_xpath = tab_xpath.xpath('.//ul[@role="tablist"]')
        if len(subtablist_xpath) == 0:
            tabs.append(FnSTab([tab_title], tab_xpath.get()))
            continue

        tabs += [
            FnSTab([tab_title] + new.path, new.content)
            for new in parse_FnS_tablist(response, subtablist_xpath)
        ]

    return tabs


# UNUSED
def parse_fees_and_scholarships(response: Response) -> list[FnSTab]:
    top_tablist = response.xpath(
        '//ul[@role="tablist" and not(ancestor::div[contains(@class, "tab-content")])]'
    )

    return parse_FnS_tablist(response, top_tablist)


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

        # pass it to the pipeline
        yield AdmissionEnItem(
            response.url, title if title is not None else response.url, main_xpath.get()
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
