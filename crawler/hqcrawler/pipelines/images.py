"""
HQImagesPipeline — estende o ImagesPipeline do Scrapy.

Responsabilidades:
  - Organiza imagens em downloads/{site}/{slug}/
  - Capa guardada como cover.jpg
  - Verifica ficheiro no disco antes de baixar (nunca re-baixa)
  - Actualiza local_path e downloaded=True na BD após download
"""

import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).parent.parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from itemadapter import ItemAdapter
from scrapy.pipelines.images import ImagesPipeline
from scrapy.http import Request

from db import crud
from db.database import session_ctx


class HQImagesPipeline(ImagesPipeline):

    def file_path(self, request, response=None, info=None, item=None):
        """
        Define o path local da imagem dentro de IMAGES_STORE:
          {site}/{slug}/cover.jpg      para a capa (primeiro URL)
          {site}/{slug}/{filename}     para as restantes
        """
        adapter  = ItemAdapter(item)
        site_key = adapter.get("site_key", "unknown")
        art_url  = adapter.get("url", "")
        site_name = "hqporno" if site_key == "hq" else "superhq"

        slug = art_url.rstrip("/").split("/")[-1]
        if slug.endswith(".html"):
            slug = slug[:-5]

        image_urls = adapter.get("image_urls", [])
        is_cover   = len(image_urls) > 0 and request.url == image_urls[0]

        filename = "cover.jpg" if is_cover else request.url.split("/")[-1]
        return f"{site_name}/{slug}/{filename}"

    def get_media_requests(self, item, info):
        """Só faz request para imagens ainda não presentes no disco."""
        adapter   = ItemAdapter(item)
        image_urls = adapter.get("image_urls", [])
        store_path = Path(info.spider.settings.get("IMAGES_STORE", "downloads"))

        for url in image_urls:
            local = store_path / self.file_path(
                Request(url), info=info, item=item
            )
            if local.exists():
                info.spider.logger.debug(f"Imagem já existe, pulando: {local}")
                continue
            yield Request(url, headers={
                "Referer": "https://www.superhq.net/",
                "Accept":  "image/webp,image/apng,image/*,*/*;q=0.8",
            })

    def item_completed(self, results, item, info):
        """Após download, actualiza local_path na BD."""
        adapter   = ItemAdapter(item)
        art_url   = adapter.get("url", "")
        site_key  = adapter.get("site_key", "")
        store_path = Path(info.spider.settings.get("IMAGES_STORE", "downloads"))

        with session_ctx() as s:
            from db import crud as _crud
            site    = _crud.get_site(s, site_key)
            article = _crud.get_article(s, art_url) if site else None
            if not article:
                return item

            images      = _crud.get_images_for_article(s, article.id)
            images_map  = {img.url: img for img in images}
            cover_local = ""

            image_urls = adapter.get("image_urls", [])

            # Marca imagens já no disco (mesmo as que não foram baixadas agora)
            for url in image_urls:
                rel_path = self.file_path(Request(url), info=info, item=item)
                full_path = store_path / rel_path
                if full_path.exists():
                    is_cover = len(image_urls) > 0 and url == image_urls[0]
                    if is_cover:
                        cover_local = rel_path
                    elif url in images_map and not images_map[url].downloaded:
                        _crud.mark_image_downloaded(s, images_map[url].id, rel_path)

            if cover_local or any(full_path.exists()
                                   for url in image_urls
                                   for full_path in [store_path / self.file_path(Request(url), info=info, item=item)]):
                _crud.mark_article_downloaded(s, article.id, cover_local)

        return item
