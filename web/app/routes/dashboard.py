"""
Dashboard — visão geral + controlo do crawler.
"""

from flask import Blueprint, jsonify, render_template, request

from db import crud
from db.database import session_ctx
from web.app.services import crawler_control

bp = Blueprint("dashboard", __name__)

SITES = {
    "hq":    {"label": "HQPorno", "base_url": "https://www.hqporno.net"},
    "super": {"label": "SuperHQ", "base_url": "https://www.superhq.net"},
}


@bp.get("/")
def dashboard():
    sites_data = []
    with session_ctx() as s:
        for key, cfg in SITES.items():
            site  = crud.get_site(s, key)
            st    = crawler_control.status(key)
            stats = crud.get_stats(s, site.id) if site else {
                "total_articles": 0, "total_images": 0, "downloaded_imgs": 0,
                "downloaded_arts": 0, "total_tags": 0, "pct_downloaded": 0,
            }
            sites_data.append({
                "key":      key,
                "label":    cfg["label"],
                "base_url": cfg["base_url"],
                "status":   st["status"],
                "running":  st["running"],
                "stats":    stats,
            })
    return render_template("dashboard.html", sites=sites_data)


@bp.get("/site/<key>")
def site_panel(key: str):
    st = crawler_control.status(key)
    with session_ctx() as s:
        site  = crud.get_site(s, key)
        stats = crud.get_stats(s, site.id) if site else {}
    return render_template("site_panel.html",
                           site_key=key, cfg=SITES[key], task=st, stats=stats)


@bp.post("/site/<key>/crawl/start")
def crawl_start(key: str):
    max_pages = int(request.form.get("max_pages", 0))
    return jsonify(crawler_control.start(key, max_pages=max_pages))


@bp.post("/site/<key>/crawl/stop")
def crawl_stop(key: str):
    return jsonify(crawler_control.stop(key))


@bp.post("/site/<key>/crawl/pause")
def crawl_pause(key: str):
    return jsonify(crawler_control.pause(key))


@bp.post("/site/<key>/crawl/resume")
def crawl_resume(key: str):
    max_pages = int(request.form.get("max_pages", 0))
    return jsonify(crawler_control.resume(key, max_pages=max_pages))


@bp.get("/site/<key>/crawl/status")
def crawl_status(key: str):
    st = crawler_control.status(key)
    with session_ctx() as s:
        site  = crud.get_site(s, key)
        stats = crud.get_stats(s, site.id) if site else {"total_articles": 0}
    st["articles"] = stats.get("total_articles", 0)
    return render_template("partials/crawl_status.html",
                           site_key=key, task=st, stats=stats)
