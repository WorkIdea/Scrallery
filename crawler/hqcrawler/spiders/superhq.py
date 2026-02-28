"""
Spider para superhq.net
"""

from hqcrawler.spiders.base import BaseHQSpider


class SuperHQSpider(BaseHQSpider):
    name             = "superhq"
    site_key         = "super"
    allowed_domains  = ["www.superhq.net", "superhq.net"]

    # Artigo: /{ano}/slug.html
    article_path_re  = r"superhq\.net/\d{4}/.+\.html$"

    # Listagem: index, paginação, categoria, tag
    listing_path_re  = r"superhq\.net(/page/\d+|/category/|/tag/|/?$)"

    start_urls = [
        "https://www.superhq.net/",
        "https://www.superhq.net/category/hentai",
        "https://www.superhq.net/category/hentai-3d",
        "https://www.superhq.net/category/cartoons",
        "https://www.superhq.net/category/incesto",
        "https://www.superhq.net/category/interracial",
        "https://www.superhq.net/category/futanari",
        "https://www.superhq.net/category/naruto",
        "https://www.superhq.net/category/milftoon",
        "https://www.superhq.net/category/familia-sacana",
        "https://www.superhq.net/category/simptoons",
        "https://www.superhq.net/category/tufos",
        "https://www.superhq.net/category/jab",
        "https://www.superhq.net/category/y3df",
        "https://www.superhq.net/category/pb",
        "https://www.superhq.net/category/hq",
        "https://www.superhq.net/category/casa-da-mae-joana-tufos",
        "https://www.superhq.net/category/marlboroman",
        "https://www.superhq.net/category/seiren",
        "https://www.superhq.net/category/antigas",
        "https://www.superhq.net/category/acompanhantes",
    ]

    def _is_real_article_card(self, article_tag) -> bool:
        """
        superhq.net: filtra pelo domínio do link.
        Anúncios apontam para tufos.com.br, filmeshentai.com, etc.
        """
        from urllib.parse import urljoin
        for a in article_tag.find_all("a", href=True):
            href = a["href"]
            if href.startswith("http") and "superhq.net" not in href:
                return False
        return True
