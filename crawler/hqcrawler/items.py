"""
Items Scrapy — estrutura dos dados extraídos pelos spiders.
"""

import scrapy


class ArticleItem(scrapy.Item):
    # Identificação
    url      = scrapy.Field()
    site_key = scrapy.Field()   # 'hq' | 'super'

    # Conteúdo
    title    = scrapy.Field()
    summary  = scrapy.Field()
    cover    = scrapy.Field()   # URL da capa

    # Relações
    tags       = scrapy.Field()   # [{"name": ..., "url": ...}]
    categories = scrapy.Field()   # [{"name": ..., "url": ...}]

    # Imagens (para ImagesPipeline)
    image_urls   = scrapy.Field()   # lista de URLs
    images_result = scrapy.Field()  # preenchido pelo ImagesPipeline


class ListingItem(scrapy.Item):
    """Registo de uma página de listagem visitada."""
    url       = scrapy.Field()
    site_key  = scrapy.Field()
    page_type = scrapy.Field()   # index | category | tag | page
    label     = scrapy.Field()
