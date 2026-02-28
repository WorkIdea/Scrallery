"""
Download — exportação de dados e imagens.
"""

import csv
import io
import json

from flask import Blueprint, Response, jsonify, request

from db import crud
from db.database import session_ctx
from web.app.services import downloader

bp = Blueprint("download", __name__)

SITES = {
    "hq":    {"name": "hqporno"},
    "super": {"name": "superhq"},
}


@bp.get("/download/article/<int:article_id>/zip")
def download_article_zip(article_id: int):
    key = request.args.get("key", "hq")
    with session_ctx() as s:
        article = crud.get_article_by_id(s, article_id)
        if not article:
            return jsonify({"error": "not found"}), 404
        data = downloader.build_zip(s, article, SITES[key]["name"])
    slug = article.url.rstrip("/").split("/")[-1]
    return Response(data, mimetype="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{slug}.zip"'})


@bp.post("/download/bulk/<key>")
def download_bulk(key: str):
    """Recebe JSON {ids: [...]} e devolve ZIP com todos os artigos."""
    ids = request.json.get("ids", [])
    with session_ctx() as s:
        articles = [a for a in (crud.get_article_by_id(s, i) for i in ids) if a]
        data     = downloader.build_zip_bulk(s, articles, SITES[key]["name"])
    return Response(data, mimetype="application/zip",
                    headers={"Content-Disposition":
                             f'attachment; filename="{SITES[key]["name"]}_bulk.zip"'})


@bp.get("/download/json/<key>")
def download_json(key: str):
    with session_ctx() as s:
        site = crud.get_site(s, key)
        arts = crud.get_articles_by_site(s, site.id, limit=99999)
        data = [{"url": a.url, "title": a.title, "summary": a.summary,
                 "cover": a.cover_url, "total_images": a.total_images} for a in arts]
    return Response(
        json.dumps(data, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition":
                 f'attachment; filename="{SITES[key]["name"]}.json"'})


@bp.get("/download/csv/<key>")
def download_csv(key: str):
    with session_ctx() as s:
        site = crud.get_site(s, key)
        arts = crud.get_articles_by_site(s, site.id, limit=99999)
    buf = io.StringIO()
    w   = csv.DictWriter(buf, fieldnames=["url","title","summary","cover",
                                           "total_images","downloaded_at"])
    w.writeheader()
    for a in arts:
        w.writerow({"url": a.url, "title": a.title, "summary": a.summary,
                    "cover": a.cover_url, "total_images": a.total_images,
                    "downloaded_at": a.downloaded_at or ""})
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition":
                             f'attachment; filename="{SITES[key]["name"]}.csv"'})
