import urllib

import scrapy
from scrapy.http import Response

from dataclasses import dataclass
from parsel.selector import SelectorList
from ..items import AdmissionEnItem


@dataclass
class FnSTab:
    path: list[str]
    content: str


class AdmissionEnSpider(scrapy.Spider):
    name = "admission_en"
    allowed_domains = ["apply.p.lodz.pl"]
    start_urls = [
        "https://apply.p.lodz.pl/en/enrollment/enroll/fees-and-scholarships",
    ]

    def parse_FnS_tablist(
        self, response: Response, tablist: SelectorList
    ) -> list[FnSTab]:
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
                for new in self.parse_FnS_tablist(response, subtablist_xpath)
            ]

        return tabs

    def parse_fees_and_scholarships(self, response: Response) -> list[FnSTab]:
        top_tablist = response.xpath(
            '//ul[@role="tablist" and not(ancestor::div[contains(@class, "tab-content")])]'
        )

        return self.parse_FnS_tablist(response, top_tablist)

    def parse_text_response(self, response: Response):
        main_xpath = response.xpath('//main[@id="content"]')
        if len(main_xpath) == 0:
            self.logger.warn("missing <main id='content'>, skipping..")
            return None

        title = response.xpath("//head//title/text()").get()

        yield AdmissionEnItem(
            response.url, title if title is not None else response.url, main_xpath.get()
        )

        for href in response.xpath("//a/@href").getall():
            href = href.strip()
            if len(href) == 0 or href[0] == "#":
                continue

            href = urllib.parse.urljoin(response.url, href)

            url = urllib.parse.urlparse(href)
            if not url.scheme.startswith("http"):
                continue
            path = url.path.split("/")[1:]

            print(path)
            # yeah, cause someone was too lazy with rewrite/redirect rules
            # rekrutacja.p.lodz.pl = polish
            # apply.p.lodz.pl/en = english
            # apply.p.lodz.pl/ = broken, polish mixed with english
            # rekrutacja.p.lodz.pl/en = polish ??
            if len(path) == 0 or path[0] != "en":
                continue

            yield response.follow(href)

    def parse(self, response: Response):
        if isinstance(response, scrapy.http.TextResponse):
            yield from self.parse_text_response(response)
        # # urlpath = urllib.parse.urlparse(response.url).path
        # if response.headers["content-type"].find("text/html".encode("utf-8")) == -1:
        #     return None
