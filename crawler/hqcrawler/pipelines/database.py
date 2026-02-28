"""
DatabasePipeline — grava ArticleItem e ListingItem na BD SQLite.
Usa crud.py partilhado — sem lógica de BD aqui.
"""

import sys
from pathlib import Path

# Adiciona a raiz do projecto ao path para encontrar db/
ROOT = Path(__file__).parent.parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db import crud
from db.database import init_db, session_ctx
from db.models import Site
from hqcrawler.items import ArticleItem, ListingItem

SITES_CFG = {
    "hq":    {"name": "hqporno", "label": "HQPorno", "base_url": "https://www.hqporno.net"},
    "super": {"name": "superhq", "label": "SuperHQ", "base_url": "https://www.superhq.net"},
}


class DatabasePipeline:

    def open_spider(self, spider):
        init_db()
        # Garante que os sites existem na BD
        with session_ctx() as s:
            for key, cfg in SITES_CFG.items():
                crud.get_or_create_site(s, key, cfg["name"], cfg["label"], cfg["base_url"])
        spider.logger.info("DatabasePipeline: BD inicializada")

    def process_item(self, item, spider):
        if isinstance(item, ArticleItem):
            self._save_article(item, spider)
        elif isinstance(item, ListingItem):
            self._save_listing(item, spider)
        return item

    def _save_article(self, item: ArticleItem, spider):
        with session_ctx() as s:
            site = crud.get_site(s, item["site_key"])
            if not site:
                return

            data = {
                "url":          item["url"],
                "title":        item.get("title", ""),
                "summary":      item.get("summary", ""),
                "cover":        item.get("cover", ""),
                "tags":         item.get("tags", []),
                "categories":   item.get("categories", []),
                "images":       item.get("image_urls", [])[1:],  # exclui capa (índice 0)
                "total_images": max(0, len(item.get("image_urls", [])) - 1),
            }

            article, created = crud.upsert_article(s, data, site.id)
            action = "criado" if created else "actualizado"
            spider.logger.debug(f"BD: artigo {action} — {item['url']}")

    def _save_listing(self, item: ListingItem, spider):
        with session_ctx() as s:
            site = crud.get_site(s, item["site_key"])
            if not site:
                return
            _, created = crud.get_or_create_listing(
                s, item["url"], site.id, item.get("page_type", "index"), item.get("label", "")
            )
            if created:
                spider.logger.debug(f"BD: listagem registada — {item['url']}")
