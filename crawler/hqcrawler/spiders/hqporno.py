"""
Spider para hqporno.net
"""

from hqcrawler.spiders.base import BaseHQSpider


class HQPornoSpider(BaseHQSpider):
    name             = "hqporno"
    site_key         = "hq"
    allowed_domains  = ["www.hqporno.net", "hqporno.net"]

    # Artigo: /slug-simples/ — letras, números e hífens, sem subpastas
    article_path_re  = r"hqporno\.net/[a-z0-9][a-z0-9\-]+/?$"

    # Listagem: index, paginação, categoria, tag
    listing_path_re  = r"hqporno\.net(/page/\d+|/category/|/tag/|/?$)"

    start_urls = [
        "https://www.hqporno.net/",
        "https://www.hqporno.net/category/hentai/",
        "https://www.hqporno.net/category/hentai-3d/",
        "https://www.hqporno.net/category/incesto/",
        "https://www.hqporno.net/category/interracial/",
        "https://www.hqporno.net/category/futanari/",
        "https://www.hqporno.net/category/hentai-gay/",
        "https://www.hqporno.net/category/parodia-porno/",
        "https://www.hqporno.net/category/preto-e-branco/",
        "https://www.hqporno.net/category/super-herois/",
        "https://www.hqporno.net/category/naruto/",
        "https://www.hqporno.net/category/dragon-ball-z/",
        "https://www.hqporno.net/category/pokemon/",
        "https://www.hqporno.net/category/tufos/",
        "https://www.hqporno.net/category/cartoon/",
        "https://www.hqporno.net/category/os-sacanas/",
        "https://www.hqporno.net/category/simptoons/",
        "https://www.hqporno.net/category/letsdoeit/",
        "https://www.hqporno.net/category/fazenda-caipira/",
        "https://www.hqporno.net/category/os-sacanas-filminho/",
    ]

    def _is_real_article_card(self, article_tag) -> bool:
        """
        hqporno.net: artigos reais têm post-ID numérico nas classes
        (ex: post-18575). Anúncios não têm.
        """
        return any(
            c.startswith("post-") and c[5:].isdigit()
            for c in article_tag.get("class", [])
        )
