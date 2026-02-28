"""
Configuração do Scrapy.
Todas as variáveis sensíveis via environment para compatibilidade com containers.
"""

import os
from pathlib import Path

BOT_NAME    = "hqcrawler"
SPIDER_MODULES    = ["hqcrawler.spiders"]
NEWSPIDER_MODULE  = "hqcrawler.spiders"

# ── Comportamento ─────────────────────────────────────────────────────────────
ROBOTSTXT_OBEY        = True
CONCURRENT_REQUESTS   = 4
DOWNLOAD_DELAY        = 2
RANDOMIZE_DOWNLOAD_DELAY = True
AUTOTHROTTLE_ENABLED  = True
AUTOTHROTTLE_START_DELAY   = 2
AUTOTHROTTLE_MAX_DELAY     = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 2

# ── Retry ─────────────────────────────────────────────────────────────────────
RETRY_ENABLED    = True
RETRY_TIMES      = 3
RETRY_HTTP_CODES = [429, 500, 502, 503, 504]

# ── Headers ───────────────────────────────────────────────────────────────────
DEFAULT_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ── Pipelines ─────────────────────────────────────────────────────────────────
ITEM_PIPELINES = {
    "hqcrawler.pipelines.database.DatabasePipeline": 300,
    "hqcrawler.pipelines.images.HQImagesPipeline":   400,
}

# ── Imagens ───────────────────────────────────────────────────────────────────
# Em container: IMAGES_STORE=/data/downloads
IMAGES_STORE = os.environ.get(
    "IMAGES_STORE",
    str(Path(__file__).parent.parent.parent.parent / "downloads")
)
IMAGES_URLS_FIELD  = "image_urls"
IMAGES_RESULT_FIELD = "images_result"

# ── Base de dados ─────────────────────────────────────────────────────────────
# Em container: DATABASE_URL=sqlite:////data/crawler.db
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{Path(__file__).parent.parent.parent.parent / 'crawler.db'}"
)

# ── Pausa/Retomada ────────────────────────────────────────────────────────────
# JOBDIR é passado via -s JOBDIR=... ou variável de ambiente
# Exemplo: scrapy crawl hqporno -s JOBDIR=jobs/hqporno
JOBDIR = os.environ.get("SCRAPY_JOBDIR", "")

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL = os.environ.get("SCRAPY_LOG_LEVEL", "INFO")
LOG_FILE  = os.environ.get("SCRAPY_LOG_FILE", "")

# ── Feed exports (opcional) ───────────────────────────────────────────────────
FEEDS = {}

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
