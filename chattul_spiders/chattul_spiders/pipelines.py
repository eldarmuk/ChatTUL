# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
# from itemadapter import ItemAdapter

# from itemadapter import ItemAdapter
import scrapy
import sqlite3
from .items import AdmissionEnItem

SQLITE_MIGRATIONS = {
    1: """
    BEGIN;
    CREATE TABLE _schema (
        version INTEGER NOT NULL
    );
    CREATE TABLE admission_en (
        id INTEGER PRIMARY KEY NOT NULL,
        url TEXT NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL
    );
    INSERT INTO _schema( version ) VALUES
        ( 1 );

    COMMIT;
    """
}
SQLITE_MIGRATION_KEYS = sorted(SQLITE_MIGRATIONS.keys())


class SqliteInsertPipeline:
    connections: dict[str, sqlite3.Connection | None]

    def __init__(self):
        self.connections = {}
        con = sqlite3.connect("crawl_items.sqlite3")
        try:
            with con as trx:
                self.upgrade_schema(trx)
        finally:
            con.close()

    def upgrade_schema(self, connection: sqlite3.Connection):
        schema_version = self.get_schema_version(connection.cursor())

        base_version = SQLITE_MIGRATION_KEYS[0]

        if schema_version == 0:
            with connection as tx:
                cur = tx.cursor()
                cur.executescript(SQLITE_MIGRATIONS[base_version])

            schema_version = base_version

        if schema_version < base_version:
            raise RuntimeError("schema version too old")

        for key in SQLITE_MIGRATION_KEYS:
            if key <= schema_version:
                continue

            with connection as tx:
                cur = tx.cursor()
                cur.executescript(SQLITE_MIGRATIONS[key])

    def get_schema_version(self, cursor: sqlite3.Cursor) -> int:
        res = cursor.execute("SELECT name FROM sqlite_master")
        res = res.fetchone()

        if res is None or "_schema" not in set(res):
            return 0

        res = cursor.execute("SELECT version FROM _schema")
        res = res.fetchone()

        return 0 if res is None else res[0]

    def open_spider(self, spider: scrapy.Spider):
        self.connections[spider.name] = sqlite3.connect("crawl_items.sqlite3")

    def close_spider(self, spider: scrapy.Spider):
        con = self.connections[spider.name]
        assert con is not None

        self.connections[spider.name] = None
        con.close()

    def process_item(self, item, spider: scrapy.Spider):
        con = self.connections[spider.name]

        assert con is not None
        con: sqlite3.Connection = con

        if isinstance(item, AdmissionEnItem):
            stmt = "INSERT INTO admission_en(url, title, content) VALUES(?, ?, ?)"
            with con as tx:
                cur = tx.cursor()
                cur.execute(stmt, (item.url, item.title, item.content))

        return item
