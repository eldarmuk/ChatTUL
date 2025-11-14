import sys
from argparse import ArgumentParser
from pathlib import Path

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from .spiders.admission_en import AdmissionEnSpider


argparser = ArgumentParser()
argparser.add_argument(
    "--pipelines",
    choices=["context_service", "PRESET-PROD"],
    help="Enable item pipelines that by default are optional",
    nargs="*",
)
argparser.add_argument(
    "-o", "--output", type=Path, help="Specify jsonline feed output path"
)

args = argparser.parse_args()

settings = get_project_settings().copy()

if args.output is not None:
    feed_output: Path = args.output
    feeds: dict = settings.get("FEEDS", {})

    if str(feed_output) in feeds:
        print(
            f"CONFLICT! {str(feed_output)} already specified by settings.py",
            file=sys.stderr,
        )
        sys.exit(1)

    feeds[str(feed_output)] = {
        "format": "jsonlines",
        "encoding": "utf-8",
        "indent": None,
    }

    settings.set("FEEDS", feeds)

PIPELINE_NAME_TO_MODULE = {
    "context_service": "crawler.pipelines.context_service.ContextServicePipeline"
}

if args.pipelines is not None:
    item_pipelines: dict = settings.get("ITEM_PIPELINES", {})
    pipelines = set(args.pipelines)

    if "PRESET-PROD" in pipelines:
        pipelines.add("context_service")

    if "context_service" in pipelines:
        item_pipelines[PIPELINE_NAME_TO_MODULE["context_service"]] = (
            max(item_pipelines.values(), default=0) + 1
        )

crawler_process = CrawlerProcess(settings)
crawler_process.crawl(AdmissionEnSpider)
crawler_process.start()
