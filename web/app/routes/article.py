"""
Article — página de detalhe com galeria, download e capítulos relacionados.
"""

from flask import Blueprint, jsonify, render_template

from db import crud
from db.database import session_ctx
from web.app.services import downloader, extractor

bp = Blueprint("article", __name__)

SITES = {
    "hq":    {"label": "HQPorno", "name": "hqporno"},
    "super": {"label": "SuperHQ", "name": "superhq"},
}


@bp.get("/article/<key>/<int:article_id>")
def article_page(key: str, article_id: int):
    with session_ctx() as s:
        article = crud.get_article_by_id(s, article_id)
        if not article:
            return "Artigo não encontrado", 404

        # Scrape completo se ainda não tiver imagens
        if article.total_images == 0:
            html = extractor.fetch(article.url)
            if html:
                data = extractor.extract_article(html, article.url)
                site = crud.get_site(s, key)
                article, _ = crud.upsert_article(s, data, site.id)

        # Imagens
        images = crud.get_images_for_article(s, article_id)
        images_display = []
        for img in images:
            src = f"/downloads/{img.local_path}" if img.downloaded and img.local_path else img.url
            images_display.append({
                "id": img.id, "src": src,
                "filename": img.filename, "downloaded": img.downloaded,
            })

        # Capa
        cover_src = ""
        if article.cover_local:
            cover_src = f"/downloads/{article.cover_local}"
        elif article.cover_url:
            cover_src = article.cover_url

        # Capítulos relacionados — artigos que partilham tags
        related_raw = crud.get_related_by_tag(s, article_id, limit=24)
        related = []
        for r in related_raw:
            r_cover = f"/downloads/{r.cover_local}" if r.cover_local else r.cover_url
            related.append({
                "id":           r.id,
                "title":        r.title,
                "cover":        r_cover,
                "total_images": r.total_images,
                "downloaded":   r.downloaded_at is not None,
            })

        return render_template("article.html",
            site_key=key,
            cfg=SITES[key],
            article=article,
            images=images_display,
            cover_src=cover_src,
            downloaded=article.downloaded_at is not None,
            pending_count=len([i for i in images if not i.downloaded]),
            related=related,
        )


@bp.post("/article/<key>/<int:article_id>/download")
def article_download(key: str, article_id: int):
    with session_ctx() as s:
        article = crud.get_article_by_id(s, article_id)
        if not article:
            return jsonify({"error": "not found"}), 404
        stats = downloader.download_article(s, article, SITES[key]["name"])
    return jsonify(stats)
