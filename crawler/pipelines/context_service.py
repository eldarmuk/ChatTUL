import scrapy
from itemadapter import ItemAdapter

import requests
import datetime
from base64 import urlsafe_b64encode, b64encode
from pydantic import BaseModel


class SourceDocument(BaseModel):
    url: str
    timestamp: int
    content: str | None = None


class ContextServicePipeline:
    """
    Item pipeline that sends items over HTTP endpoint to be saved by context service.
    """

    item_meta_cache: dict[str, SourceDocument]
    service_url: str

    def __init__(self, service_hostname: str, service_port: int):
        self.item_meta_cache = {}
        self.service_url = f"{service_hostname}:{service_port}"

        resp = self._get("/health")
        assert resp.status_code == 200

    @classmethod
    def from_crawler(cls, crawler: scrapy.crawler.Crawler):
        return cls(
            crawler.settings.get("CONTEXT_SERVICE_HOSTNAME"),
            crawler.settings.get("CONTEXT_SERVICE_PORT"),
        )

    def _put(self, path: str, *args, **kwargs) -> requests.Response:
        return requests.put(self.service_url + path, *args, **kwargs)

    def _get(self, path: str, *args, **kwargs) -> requests.Response:
        return requests.get(self.service_url + path, *args, **kwargs)

    def fetch_item_meta(self, url: str) -> SourceDocument | None:
        """
        Fetch item metadata without it's content.

        Caches item metadata in 'self.item_meta_cache' dict
        """
        if url in self.item_meta_cache:
            return self.item_meta_cache[url]

        resp = self._get(
            f"/index/{urlsafe_b64encode(url.encode('utf-8')).decode('utf-8')}?no_content=1"
        )
        if resp.status_code == 404:
            return None
        assert resp.status_code == 200

        meta = SourceDocument.parse_raw(resp.text)

        self.item_meta_cache[url] = meta
        return meta

    def process_item(self, item, spider: scrapy.Spider):
        adapter = ItemAdapter(item)
        if adapter.get("url") is None:
            raise scrapy.DropItem("missing `url` field")
        if adapter.get("content") is None:
            raise scrapy.DropItem("missing `content` field")

        url = adapter["url"]
        content = adapter["content"]
        timestamp = (
            adapter.get("timestamp")
            or (
                datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)
            ).total_seconds()
            // 1
        )

        meta = self.fetch_item_meta(url)
        if meta is None or meta.get("timestamp") < timestamp:
            resp = self._put(
                f"/index/{urlsafe_b64encode(url.encode('utf-8')).decode('utf-8')}",
                json={
                    "timestamp": timestamp,
                    "content": b64encode(content.encode("utf-8")).decode("utf-8"),
                },
            )
            if resp.status_code == 422:
                print(resp.json())

            assert resp.status_code == 200
            self.item_meta_cache[url] = SourceDocument(url=url, timestamp=timestamp)
        return item
