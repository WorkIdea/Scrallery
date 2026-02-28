"""
Extractor — usado pelo modo navegar da web.
Mesma lógica do spider base mas sem dependências Scrapy.
Completamente independente — pode ser trocado sem afectar o crawler.
"""

import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

IMAGE_PATTERN = re.compile(
    r'https://static\.superhq\.net/galerias/[^\s"\'<>]+\.(?:jpg|jpeg|png|gif|webp)',
    re.IGNORECASE,
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}


def fetch(url: str, retries: int = 3) -> str | None:
    """HTTP GET simples com retry."""
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code == 200:
                return resp.text
            if resp.status_code == 404:
                return None
        except requests.RequestException:
            if attempt == retries - 1:
                return None
    return None


def extract_listing(html: str, current_url: str, site_key: str) -> dict:
    """
    Extrai de uma página de listagem:
      articles   — lista de dicts com url, title, summary, cover
      listings   — outras listagens descobertas (cats/tags)
      next_page  — próxima página ou None
    """
    soup = BeautifulSoup(html, "html.parser")
    articles  = []
    listings  = []

    # Próxima página
    next_page = None
    link_next = soup.find("link", rel="next")
    if link_next and link_next.get("href"):
        next_page = link_next["href"].split("#")[0]
    if not next_page:
        for a in soup.find_all("a", href=True):
            txt = a.get_text(strip=True).lower()
            if txt in ("»", "›", "next", "próximo", "→", "older posts"):
                href = urljoin(current_url, a["href"]).split("#")[0]
                if _is_listing(href, site_key):
                    next_page = href
                    break

    # Categorias e tags da navegação
    for zone in soup.find_all(["nav", "aside", "footer", "header"]):
        for a in zone.find_all("a", href=True):
            href = urljoin(current_url, a["href"]).split("#")[0].split("?")[0]
            if _is_listing(href, site_key):
                listings.append(href)

    # Artigos nos cards
    for article_tag in soup.find_all("article"):
        if site_key == "hq":
            if not any(c.startswith("post-") and c[5:].isdigit()
                       for c in article_tag.get("class", [])):
                continue

        art_url = None
        for a in article_tag.find_all("a", href=True):
            href = urljoin(current_url, a["href"]).split("#")[0].split("?")[0]
            if _is_article(href, site_key):
                art_url = href
                break
        if not art_url:
            continue

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
                cover = urljoin(current_url, src)
                break

        articles.append({"url": art_url, "title": title,
                          "summary": summary, "cover": cover})

    return {"articles": articles, "listings": list(set(listings)), "next_page": next_page}


def extract_article(html: str, url: str) -> dict:
    """Extrai dados completos de um artigo."""
    soup    = BeautifulSoup(html, "html.parser")

    # Título
    title = ""
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(strip=True)
    elif soup.find("title"):
        title = soup.find("title").get_text(strip=True)

    # Resumo
    summary = ""
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        summary = meta["content"].strip()

    # Capa
    cover = ""
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        cover = og["content"].strip()
    if not cover:
        wp = soup.find("img", class_=lambda c: c and "wp-post-image" in c)
        if wp:
            cover = wp.get("data-src") or wp.get("src", "")
    if not cover:
        container = soup.find("article") or soup
        for img in container.find_all("img", limit=5):
            src = img.get("data-src") or img.get("src", "")
            if src and not src.startswith("data:") and not src.endswith(".svg"):
                cover = urljoin(url, src)
                break

    # Taxonomy
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

    # Imagens
    seen_i: set = set()
    images = []
    for img_url in IMAGE_PATTERN.findall(str(soup)):
        if img_url not in seen_i:
            seen_i.add(img_url)
            images.append(img_url)

    def _sort_key(u):
        name = u.split("/")[-1].rsplit(".", 1)[0]
        try:    return (int(name),)
        except: return (0,)

    images.sort(key=_sort_key)

    return {
        "url": url, "title": title, "summary": summary, "cover": cover,
        "tags": tags, "categories": cats,
        "images": images, "total_images": len(images),
    }


def page_type(url: str) -> str:
    if "/category/" in url: return "category"
    if "/tag/"      in url: return "tag"
    if "/page/"     in url: return "page"
    return "index"


def page_label(url: str) -> str:
    for marker in ("/category/", "/tag/"):
        if marker in url:
            part = url.split(marker)[-1].rstrip("/").split("/")[0]
            return part.replace("-", " ").title()
    return ""


def prev_page_url(url: str) -> str | None:
    m = re.search(r"/page/(\d+)", url)
    if m:
        n    = int(m.group(1))
        base = url[:m.start()]
        if n > 2: return f"{base}/page/{n - 1}"
        if n == 2: return base
    return None


def _is_article(url: str, site_key: str) -> bool:
    if site_key == "hq":
        return bool(re.search(r"hqporno\.net/[a-z0-9][a-z0-9\-]+/?$", url))
    return bool(re.search(r"superhq\.net/\d{4}/.+\.html$", url))


def _is_listing(url: str, site_key: str) -> bool:
    if site_key == "hq":
        return bool(re.search(r"hqporno\.net(/page/\d+|/category/|/tag/|/?$)", url))
    return bool(re.search(r"superhq\.net(/page/\d+|/category/|/tag/|/?$)", url))


def extract_nav_links(html: str, current_url: str, site_key: str) -> tuple[list, list]:
    """
    Extrai categorias e tags da navegação da página ao vivo.
    Retorna (categories, tags) — cada item: {"name": str, "url": str}
    Usado pelo browse para preencher a sidebar com links reais do site.
    """
    soup = BeautifulSoup(html, "html.parser")
    cats, tags = [], []
    seen_c, seen_t = set(), set()

    # Procura em nav, aside, header, footer e menus
    for zone in soup.find_all(["nav", "aside", "header", "footer",
                                "ul", "div"], limit=40):
        for a in zone.find_all("a", href=True):
            name = a.get_text(strip=True)
            href = a["href"]
            if not name or len(name) > 60:
                continue
            full = urljoin(current_url, href).split("#")[0].split("?")[0]
            if "/category/" in full and name not in seen_c:
                cats.append({"name": name, "url": full})
                seen_c.add(name)
            elif "/tag/" in full and name not in seen_t:
                tags.append({"name": name, "url": full})
                seen_t.add(name)

    return cats, tags
