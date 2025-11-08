import scrapy
from itemadapter import ItemAdapter

import requests

import os
import datetime
from base64 import urlsafe_b64encode, b64encode
from typing import TypedDict

CONTEXT_SERVICE_HOSTNAME = (
    os.getenv("CONTEXT_SERVICE_HOSTNAME") or "http://localhost"
).rstrip("/")
CONTEXT_SERVICE_PORT = int(os.getenv("CONTEXT_SERVICE_POST") or 8001)
CONTEXT_SERVICE_URL = f"{CONTEXT_SERVICE_HOSTNAME}:{CONTEXT_SERVICE_PORT}"


def _validate_http_response(resp: requests.Response) -> requests.Response:
    assert resp.headers.get("Content-Type") == "application/json"
    return resp


def _put(path: str, *args, **kwargs) -> requests.Response:
    return _validate_http_response(
        requests.put(CONTEXT_SERVICE_URL + path, *args, **kwargs)
    )


def _get(path: str, *args, **kwargs) -> requests.Response:
    return _validate_http_response(
        requests.get(CONTEXT_SERVICE_URL + path, *args, **kwargs)
    )


class ItemMeta(TypedDict):
    url: str
    timestamp: datetime.datetime


class ContextServicePipeline:
    """
    Item pipeline that sends items over HTTP endpoint to be saved by context service.
    """

    item_meta_cache: dict[str, ItemMeta]

    def __init__(self):
        resp = _get("/health")
        assert resp.status_code == 200

        self.item_meta_cache = {}

    def fetch_item_meta(self, url: str) -> ItemMeta | None:
        """
        Fetch item metadata without it's content.

        Caches item metadata in 'self.item_meta_cache' dict
        """
        if url in self.item_meta_cache:
            return self.item_meta_cache[url]

        resp = _get(
            f"/index/{urlsafe_b64encode(url.encode('utf-8')).decode('utf-8')}?no_content=1"
        )
        if resp.status_code == 404:
            return None
        assert resp.status_code == 200

        body = resp.json()
        # TODO: what to do if context service returns object in invalid schema??
        assert isinstance(body, dict)
        assert body.get("url") == url
        assert body.get("timestamp") is not None

        meta = ItemMeta(url=body["url"], timestamp=body["timestamp"])
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
            resp = _put(
                f"/index/{urlsafe_b64encode(url.encode('utf-8')).decode('utf-8')}",
                json={
                    "url": url,
                    "timestamp": timestamp,
                    "content": b64encode(content.encode("utf-8")).decode("utf-8"),
                },
            )
            if resp.status_code == 422:
                print(resp.json())

            assert resp.status_code == 200
            self.item_meta_cache[url] = ItemMeta(url=url, timestamp=timestamp)
        return item
