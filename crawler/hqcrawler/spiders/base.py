"""
BaseHQSpider — lógica comum partilhada pelos dois spiders.

Fase 1:
  - Tags seguidas como listagens (descoberta de capítulos de uma história)
  - Paginação dentro de páginas de tags
  - Stats em tempo real gravadas na BD (CrawlerJob)
  - Logs estruturados por etapa
"""

import re
from urllib.parse import urljoin

import scrapy
from bs4 import BeautifulSoup

from hqcrawler.items import ArticleItem, ListingItem

IMAGE_PATTERN = re.compile(
    r'https://static\.superhq\.net/galerias/[^\s"\'<>]+\.(?:jpg|jpeg|png|gif|webp)',
    re.IGNORECASE,
)


class BaseHQSpider(scrapy.Spider):
    """
    Atributos obrigatórios nos spiders filhos:
      name             — 'hqporno' | 'superhq'
      site_key         — 'hq' | 'super'
      allowed_domains
      start_urls
      article_path_re  — regex que identifica o path de um artigo
      listing_path_re  — regex que identifica o path de uma listagem
    """

    _pages_crawled  = 0
    _articles_found = 0
    _articles_saved = 0
    _job_id         = None

    # ── Classificação ─────────────────────────────────────────────────────────

    def is_article(self, url: str) -> bool:
        return bool(re.search(self.article_path_re, url))

    def is_listing(self, url: str) -> bool:
        return bool(re.search(self.listing_path_re, url))

    # ── Arranque ──────────────────────────────────────────────────────────────

    def start_requests(self):
        self._register_job()
        for url in self.start_urls:
            yield scrapy.Request(url, callback=self.parse)

    def _register_job(self):
        try:
            import sys
            from pathlib import Path
            ROOT = Path(__file__).parent.parent.parent.parent
            if str(ROOT) not in sys.path:
                sys.path.insert(0, str(ROOT))
            from db import crud
            from db.database import session_ctx
            with session_ctx() as s:
                job = crud.create_job(s, self.site_key, jobdir="")
                self._job_id = job.id
                self.logger.info(f"Job registado: id={self._job_id}")
        except Exception as e:
            self.logger.warning(f"Não foi possível registar job: {e}")

    def _update_job_stats(self):
        if not self._job_id or self._pages_crawled % 10 != 0:
            return
        try:
            from db import crud
            from db.database import session_ctx
            with session_ctx() as s:
                crud.update_job(s, self._job_id,
                    pages_crawled=self._pages_crawled,
                    articles_found=self._articles_found,
                    articles_saved=self._articles_saved,
                )
        except Exception:
            pass

    # ── Roteador ──────────────────────────────────────────────────────────────

    def parse(self, response):
        if self.is_article(response.url):
            yield from self.parse_article(response)
        else:
            yield from self.parse_listing(response)

    # ── Listagem ──────────────────────────────────────────────────────────────

    def parse_listing(self, response):
        """
        Extrai artigos, segue paginação e descobre novas listagens.
        Tags são tratadas exactamente como categorias.
        """
        soup      = BeautifulSoup(response.text, "html.parser")
        page_type = self._page_type(response.url)
        label     = self._page_label(response.url)
        self._pages_crawled += 1

        self.logger.info(f"[{page_type}] {label or response.url} ({self._pages_crawled} páginas)")

        yield ListingItem(
            url=response.url,
            site_key=self.site_key,
            page_type=page_type,
            label=label,
        )

        # Artigos nos cards
        found = 0
        for article_tag in soup.find_all("article"):
            if not self._is_real_article_card(article_tag):
                continue
            link = self._extract_card_link(article_tag, response.url)
            if not link:
                continue
            found += 1
            self._articles_found += 1
            yield response.follow(
                link,
                callback=self.parse_article,
                cb_kwargs={"card_data": self._extract_card_data(article_tag, response.url)},
            )

        self.logger.info(f"[{page_type}] {found} artigos encontrados")

        # Paginação
        next_page = self._next_page(soup, response.url)
        if next_page:
            yield response.follow(next_page, callback=self.parse_listing)

        # Outras listagens na sidebar/nav (categorias e tags)
        for zone in soup.find_all(["nav", "aside", "footer", "header"]):
            for a in zone.find_all("a", href=True):
                href = urljoin(response.url, a["href"]).split("#")[0].split("?")[0]
                if self.is_listing(href):
                    yield response.follow(href, callback=self.parse_listing)

        self._update_job_stats()

    # ── Artigo ────────────────────────────────────────────────────────────────

    def parse_article(self, response, card_data: dict = None):
        """
        Extrai dados completos.
        Após extrair as tags, enfileira cada página de tag —
        garante que todos os capítulos da mesma história são descobertos.
        """
        soup      = BeautifulSoup(response.text, "html.parser")
        card_data = card_data or {}

        title    = self._extract_title(soup)               or card_data.get("title", "")
        summary  = self._extract_summary(soup)             or card_data.get("summary", "")
        cover    = self._extract_cover(soup, response.url) or card_data.get("cover", "")
        tags, categories = self._extract_taxonomy(soup)
        images           = self._extract_images(response.text)

        self._articles_saved += 1
        self.logger.info(f"[artigo] '{title[:50]}' | {len(images)} imgs | {len(tags)} tags")

        yield ArticleItem(
            url=response.url,
            site_key=self.site_key,
            title=title,
            summary=summary,
            cover=cover,
            tags=tags,
            categories=categories,
            image_urls=([cover] + images) if cover else images,
        )

        # ── Chave da Fase 1 ───────────────────────────────────────────────────
        # Cada tag do artigo é uma página de listagem que agrupa capítulos.
        # Seguimos para garantir que todos os caps da história são crawleados.
        for tag in tags:
            tag_url = tag.get("url", "")
            if not tag_url:
                continue
            if tag_url.startswith("/"):
                tag_url = urljoin(response.url, tag_url)
            if self.is_listing(tag_url):
                self.logger.debug(f"[tag→listagem] '{tag['name']}' → {tag_url}")
                yield response.follow(tag_url, callback=self.parse_listing)

        self._update_job_stats()

    # ── Extracção ─────────────────────────────────────────────────────────────

    def _extract_title(self, soup) -> str:
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)
        t = soup.find("title")
        return t.get_text(strip=True) if t else ""

    def _extract_summary(self, soup) -> str:
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            return meta["content"].strip()
        return ""

    def _extract_cover(self, soup, base_url: str) -> str:
        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            return og["content"].strip()
        wp = soup.find("img", class_=lambda c: c and "wp-post-image" in c)
        if wp:
            src = wp.get("data-src") or wp.get("src", "")
            if src and not src.startswith("data:"):
                return urljoin(base_url, src)
        container = soup.find("article") or soup.find("figure") or soup
        for img in container.find_all("img", limit=5):
            src = img.get("data-src") or img.get("src", "")
            if src and not src.startswith("data:") and not src.endswith(".svg"):
                return urljoin(base_url, src)
        return ""

    def _extract_taxonomy(self, soup) -> tuple[list, list]:
        tags, cats = [], []
        seen_t, seen_c = set(), set()
        for a in soup.find_all("a", href=True):
            name = a.get_text(strip=True)
            href = a["href"]
            if not name:
                continue
            if "/tag/" in href and name not in seen_t:
                tags.append({"name": name, "url": href})
                seen_t.add(name)
            elif "/category/" in href and name not in seen_c:
                cats.append({"name": name, "url": href})
                seen_c.add(name)
        return tags, cats

    def _extract_images(self, html: str) -> list[str]:
        seen:   set[str] = set()
        images: list[str] = []
        for url in IMAGE_PATTERN.findall(html):
            if url not in seen:
                seen.add(url)
                images.append(url)

        def _sort_key(u: str):
            name = u.split("/")[-1].rsplit(".", 1)[0]
            try:    return (0, int(name))
            except: return (1, 0)

        images.sort(key=_sort_key)
        return images

    def _extract_card_link(self, article_tag, base_url: str) -> str | None:
        for a in article_tag.find_all("a", href=True):
            href = urljoin(base_url, a["href"]).split("#")[0].split("?")[0]
            if self.is_article(href):
                return href
        return None

    def _extract_card_data(self, article_tag, base_url: str) -> dict:
        title = ""
        for tag in ("h2", "h3", "h1"):
            t = article_tag.find(tag)
            if t:
                title = t.get_text(strip=True)
                break
        summary = ""
        for cls in ("entry-summary", "entry-excerpt", "post-excerpt"):
            s = article_tag.find(class_=cls)
            if s:
                summary = s.get_text(strip=True)
                break
        cover = ""
        for img in article_tag.find_all("img", limit=3):
            src = img.get("data-src") or img.get("src", "")
            if src and not src.startswith("data:") and not src.endswith(".svg"):
                cover = urljoin(base_url, src)
                break
        return {"title": title, "summary": summary, "cover": cover}

    # ── Paginação ─────────────────────────────────────────────────────────────

    def _next_page(self, soup, current_url: str) -> str | None:
        link_next = soup.find("link", rel="next")
        if link_next and link_next.get("href"):
            href = link_next["href"].split("#")[0]
            if self.is_listing(href):
                return href
        for a in soup.find_all("a", href=True):
            txt = a.get_text(strip=True).lower()
            if txt in ("»", "›", "next", "próximo", "→", "older posts", "próxima"):
                href = urljoin(current_url, a["href"]).split("#")[0]
                if self.is_listing(href):
                    return href
        return None

    def _page_type(self, url: str) -> str:
        if "/category/" in url: return "category"
        if "/tag/"      in url: return "tag"
        if "/page/"     in url: return "page"
        return "index"

    def _page_label(self, url: str) -> str:
        for marker in ("/category/", "/tag/"):
            if marker in url:
                part = url.split(marker)[-1].rstrip("/").split("/")[0]
                return part.replace("-", " ").title()
        return ""

    def _is_real_article_card(self, article_tag) -> bool:
        return True

    # ── Fecho ─────────────────────────────────────────────────────────────────

    def closed(self, reason):
        self.logger.info(
            f"Spider encerrado: {reason} | "
            f"páginas={self._pages_crawled} | "
            f"encontrados={self._articles_found} | "
            f"guardados={self._articles_saved}"
        )
        if not self._job_id:
            return
        try:
            from db import crud
            from db.database import session_ctx
            from datetime import datetime
            status = "done" if reason == "finished" else "paused"
            with session_ctx() as s:
                crud.update_job(s, self._job_id,
                    status=status,
                    ended_at=datetime.now(),
                    pages_crawled=self._pages_crawled,
                    articles_found=self._articles_found,
                    articles_saved=self._articles_saved,
                )
        except Exception as e:
            self.logger.error(f"Erro ao fechar job: {e}")
