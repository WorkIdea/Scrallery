"""
CrawlerControl — lança e gere processos Scrapy como subprocessos.
"""

import os
import signal
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT     = Path(__file__).parent.parent.parent.parent  # /app em container, raiz local
JOBS_DIR = Path(os.environ.get("SCRAPY_JOBDIR", str(ROOT / "jobs")))
JOBS_DIR.mkdir(parents=True, exist_ok=True)

# Crawler está em /app/crawler dentro do container
CRAWLER_DIR = ROOT / "crawler"

_pids: dict[str, int] = {}

SPIDER_NAMES = {"hq": "hqporno", "super": "superhq"}


def _env() -> dict:
    e = os.environ.copy()
    e.setdefault("DATABASE_URL",   f"sqlite:///{ROOT / 'crawler.db'}")
    e.setdefault("IMAGES_STORE",   str(ROOT / "downloads"))
    e.setdefault("PYTHONPATH",     str(ROOT))
    return e


def start(site_key: str, max_pages: int = 0) -> dict:
    if is_running(site_key):
        return {"ok": False, "error": "Já está a correr"}

    spider  = SPIDER_NAMES[site_key]
    job_dir = str(JOBS_DIR / site_key)
    Path(job_dir).mkdir(exist_ok=True)

    cmd = [sys.executable, "-m", "scrapy", "crawl", spider,
           "-s", f"JOBDIR={job_dir}"]
    if max_pages:
        cmd += ["-s", f"CLOSESPIDER_PAGECOUNT={max_pages}"]

    proc = subprocess.Popen(
        cmd, cwd=str(CRAWLER_DIR), env=_env(),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    _pids[site_key] = proc.pid

    from db.database import session_ctx
    from db import crud
    with session_ctx() as s:
        prev = crud.get_latest_job(s, site_key)
        if prev and prev.status == "running":
            crud.update_job(s, prev.id, status="interrupted", ended_at=datetime.now())
        crud.create_job(s, site_key, job_dir)

    return {"ok": True, "pid": proc.pid}


def stop(site_key: str) -> dict:
    pid = _pids.get(site_key)
    if not pid:
        return {"ok": False, "error": "Processo não encontrado"}
    try:
        os.kill(pid, signal.SIGTERM)
        del _pids[site_key]
        _update_job_status(site_key, "done")
        return {"ok": True}
    except ProcessLookupError:
        del _pids[site_key]
        return {"ok": False, "error": "Processo já terminou"}


def pause(site_key: str) -> dict:
    result = stop(site_key)
    if result["ok"]:
        _update_job_status(site_key, "paused")
    return result


def resume(site_key: str, max_pages: int = 0) -> dict:
    return start(site_key, max_pages)


def is_running(site_key: str) -> bool:
    pid = _pids.get(site_key)
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        del _pids[site_key]
        return False


def status(site_key: str) -> dict:
    from db.database import session_ctx
    from db import crud
    running = is_running(site_key)
    with session_ctx() as s:
        job      = crud.get_latest_job(s, site_key)
        site     = crud.get_site(s, site_key)
        articles = crud.count_articles(s, site.id) if site else 0
        if not job:
            return {"status": "idle", "running": False, "articles": articles,
                    "pages_crawled": 0, "articles_found": 0, "articles_saved": 0,
                    "started_at": None, "error": ""}
        if job.status == "running" and not running:
            crud.update_job(s, job.id, status="done", ended_at=datetime.now())
            job.status = "done"
        return {
            "status":         job.status,
            "running":        running,
            "articles":       articles,
            "pages_crawled":  job.pages_crawled,
            "articles_found": job.articles_found,
            "articles_saved": job.articles_saved,
            "started_at":     job.started_at.isoformat() if job.started_at else None,
            "ended_at":       job.ended_at.isoformat()   if job.ended_at   else None,
            "error":          job.error_msg,
        }


def _update_job_status(site_key: str, new_status: str):
    from db.database import session_ctx
    from db import crud
    with session_ctx() as s:
        job = crud.get_latest_job(s, site_key)
        if job:
            crud.update_job(s, job.id, status=new_status,
                            ended_at=datetime.now() if new_status in ("done", "error") else None)
