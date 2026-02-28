"""
Browse — navegação interactiva ao vivo.

Faz fetch à página real do site, extrai artigos e links.
A sidebar mostra:
  - Categorias/tags extraídas da página actual (ao vivo)
  - Mais categorias/tags da BD (se existirem)
A BD é usada apenas para enriquecer os dados (capa local, estado downloaded).
"""

from flask import Blueprint, render_template, request
from urllib.parse import urljoin

from db import crud
from db.database import session_ctx
from web.app.services import extractor

bp = Blueprint("browse", __name__)

SITES = {
    "hq":    {
        "label":    "HQPorno",
        "base_url": "https://www.hqporno.net",
        "index":    "https://www.hqporno.net/",
    },
    "super": {
        "label":    "SuperHQ",
        "base_url": "https://www.superhq.net",
        "index":    "https://www.superhq.net/",
    },
}


@bp.get("/browse/<key>")
def browse_index(key: str):
    return _browse(key, SITES[key]["index"])


@bp.get("/browse/<key>/navigate")
def browse_navigate(key: str):
    url = request.args.get("url", SITES[key]["index"])
    # Limpa fragmentos e query strings que não sejam paginação
    url = url.split("#")[0]
    return _browse(key, url)


def _browse(key: str, url: str):
    cfg   = SITES[key]
    label = extractor.page_label(url) or cfg["label"]

    # ── Fetch ao vivo ─────────────────────────────────────────────────────────
    html = extractor.fetch(url)

    if html is None:
        # Mesmo sem HTML mostramos a sidebar com dados da BD
        with session_ctx() as s:
            site = crud.get_site(s, key)
            cats = crud.get_categories_by_site(s, site.id) if site else []
            tags = crud.get_tags_by_site(s, site.id) if site else []
        return render_template("browse.html",
            site_key=key, cfg=cfg, url=url,
            articles=[], live_cats=[], live_tags=[],
            db_cats=cats, db_tags=tags,
            next_page=None, prev_page=None,
            page_label=label,
            error="Não foi possível carregar a página. Verifica a ligação.",
        )

    # ── Extracção da página ao vivo ───────────────────────────────────────────
    result    = extractor.extract_listing(html, url, key)
    next_page = result["next_page"]
    prev_page = extractor.prev_page_url(url)

    # Categorias e tags extraídas ao vivo desta página
    live_cats, live_tags = extractor.extract_nav_links(html, url, key)

    # ── BD: enriquecer artigos e guardar novas listagens ──────────────────────
    articles_display = []
    with session_ctx() as s:
        site = crud.get_site(s, key)

        if site:
            # Regista listagem actual
            crud.get_or_create_listing(
                s, url, site.id,
                extractor.page_type(url), label
            )
            # Regista novas listagens descobertas ao vivo
            for l_url in result["listings"]:
                crud.get_or_create_listing(
                    s, l_url, site.id,
                    extractor.page_type(l_url),
                    extractor.page_label(l_url),
                )

        # Enriquece artigos: se já está na BD usa dados locais (capa, downloaded)
        for art in result["articles"]:
            existing = crud.get_article(s, art["url"]) if site else None
            if existing:
                articles_display.append({
                    "id":           existing.id,
                    "url":          existing.url,
                    "title":        existing.title or art["title"],
                    "summary":      existing.summary or art["summary"],
                    "cover":        f"/downloads/{existing.cover_local}"
                                    if existing.cover_local else art["cover"],
                    "total_images": existing.total_images,
                    "downloaded":   existing.downloaded_at is not None,
                })
            else:
                # Artigo ainda não está na BD — guarda entrada básica
                if site:
                    obj, _ = crud.upsert_article(s, {
                        "url":          art["url"],
                        "title":        art["title"],
                        "summary":      art["summary"],
                        "cover":        art["cover"],
                        "total_images": 0,
                        "tags": [], "categories": [], "images": [],
                    }, site.id)
                    art_id = obj.id
                else:
                    art_id = None
                articles_display.append({
                    "id":           art_id,
                    "url":          art["url"],
                    "title":        art["title"],
                    "summary":      art["summary"],
                    "cover":        art["cover"],
                    "total_images": 0,
                    "downloaded":   False,
                })

        if site:
            crud.mark_listing_crawled(s, url, len(articles_display))

        # Tags e categorias da BD para complementar a sidebar
        db_cats = crud.get_categories_by_site(s, site.id) if site else []
        db_tags = crud.get_tags_by_site(s, site.id) if site else []

    return render_template("browse.html",
        site_key=key, cfg=cfg, url=url,
        articles=articles_display,
        live_cats=live_cats,
        live_tags=live_tags,
        db_cats=db_cats,
        db_tags=db_tags,
        next_page=next_page,
        prev_page=prev_page,
        page_label=label,
        error=None,
    )
