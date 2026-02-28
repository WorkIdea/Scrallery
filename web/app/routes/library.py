"""
Library — todos os artigos na BD com pesquisa, filtros e ordenação.
"""

from flask import Blueprint, render_template, request

from db import crud
from db.database import session_ctx

bp = Blueprint("library", __name__)

SITES = {
    "hq":    {"label": "HQPorno", "name": "hqporno"},
    "super": {"label": "SuperHQ", "name": "superhq"},
}
PER_PAGE = 48


@bp.get("/library/<key>")
def library(key: str):
    search         = request.args.get("q", "").strip()
    tag_id         = request.args.get("tag_id", type=int)
    category_id    = request.args.get("category_id", type=int)
    sort           = request.args.get("sort", "recent")
    downloaded_only = request.args.get("downloaded", "0") == "1"
    page           = request.args.get("page", 1, type=int)
    offset         = (page - 1) * PER_PAGE

    with session_ctx() as s:
        site = crud.get_site(s, key)
        if not site:
            return "Site não encontrado", 404

        articles = crud.get_articles_by_site(
            s, site.id,
            limit=PER_PAGE, offset=offset,
            search=search, tag_id=tag_id,
            category_id=category_id, sort=sort,
            downloaded_only=downloaded_only,
        )
        total = crud.count_articles_filtered(
            s, site.id,
            search=search, tag_id=tag_id,
            category_id=category_id,
            downloaded_only=downloaded_only,
        )

        categories = crud.get_categories_by_site(s, site.id)
        tags       = crud.get_tags_by_site(s, site.id)
        stats      = crud.get_stats(s, site.id)

        # Enriquece artigos com cover src
        arts_display = []
        for a in articles:
            cover = f"/downloads/{a.cover_local}" if a.cover_local else a.cover_url
            arts_display.append({
                "id":           a.id,
                "url":          a.url,
                "title":        a.title,
                "summary":      a.summary,
                "cover":        cover,
                "total_images": a.total_images,
                "downloaded":   a.downloaded_at is not None,
            })

        total_pages = (total + PER_PAGE - 1) // PER_PAGE

    return render_template("library.html",
        site_key=key, cfg=SITES[key],
        articles=arts_display,
        categories=categories, tags=tags,
        stats=stats,
        # Filtros activos
        search=search, tag_id=tag_id,
        category_id=category_id, sort=sort,
        downloaded_only=downloaded_only,
        # Paginação
        page=page, total_pages=total_pages, total=total,
    )
