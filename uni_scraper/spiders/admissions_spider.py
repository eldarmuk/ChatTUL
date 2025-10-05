import scrapy
from datetime import datetime
from urllib.parse import urljoin, urlparse
# from pdfminer.high_level import extract_text
# import io


class AdmissionsSpider(scrapy.Spider):
    name = "admissions_spider"
    allowed_domains = [
        "apply.p.lodz.pl",
        # "p.lodz.pl",
    ]

    start_urls = [
        "https://apply.p.lodz.pl/en/enrollment/enroll/fees-and-scholarships",
        # "https://p.lodz.pl/en/students/academic-year-calendar",
    ]

    custom_settings = {
        "DEPTH_LIMIT": 2,
        # "CLOSESPIDER_PAGECOUNT": 50,
    }

    def parse(self, response):
        content_type = response.headers.get("Content-Type", b"").decode("utf-8").lower()

        # --- PDF extraction ---
        # if "application/pdf" in content_type or response.url.lower().endswith(".pdf"):
        #     yield self.parse_pdf(response)
        #     return

        # Handle HTML pages
        if "text/html" in content_type:
            yield {
                "source_url": response.url,
                "status_code": response.status,
                "raw_html": response.text,
                "crawl_date": datetime.utcnow().isoformat(),
                "is_pdf": False,
                "pdf_text": None,
            }

            # Follow links within allowed domains
            for link in response.css("a::attr(href)").getall():
                url = self.clean_url(response.url, link)
                if not url:
                    continue
                if url.endswith((".pdf", ".doc", ".docx", ".xls", ".xlsx", ".jpg", ".png", ".gif")):
                    continue
                if any(domain in url for domain in self.allowed_domains):
                    yield response.follow(url, callback=self.parse)

    # --- PDF handling ---
    # def parse_pdf(self, response):
    #     """Extract text from PDF using pdfminer"""
    #     try:
    #         pdf_text = extract_text(io.BytesIO(response.body))
    #     except Exception as e:
    #         pdf_text = f"Error extracting PDF: {e}"
    #
    #     return {
    #         "source_url": response.url,
    #         "status_code": response.status,
    #         "raw_html": None,
    #         "crawl_date": datetime.utcnow().isoformat(),
    #         "is_pdf": True,
    #         "pdf_text": pdf_text,
    #     }

    def clean_url(self, base, link):
        """Normalize and join relative links, strip fragments"""
        if not link:
            return None
        url = urljoin(base, link)
        parsed = urlparse(url)
        return parsed._replace(fragment="").geturl()
