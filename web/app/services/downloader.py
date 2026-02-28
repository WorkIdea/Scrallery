"""
Downloader — usado pelo modo navegar para baixar imagens manualmente.
Verifica BD e filesystem antes de ir à web.
"""

import io
import os
import time
import zipfile
from pathlib import Path

import requests

# Usa variável de ambiente — funciona local e em container
DOWNLOADS_ROOT = Path(os.environ.get(
    "DOWNLOADS_ROOT",
    str(Path(__file__).parent.parent.parent.parent / "downloads")
))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer":    "https://www.superhq.net/",
}


def article_folder(site_name: str, article_url: str) -> Path:
    slug = article_url.rstrip("/").split("/")[-1]
    if slug.endswith(".html"):
        slug = slug[:-5]
    folder = DOWNLOADS_ROOT / site_name / slug
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def relative_path(folder: Path, filename: str) -> str:
    return str((folder / filename).relative_to(DOWNLOADS_ROOT))


def _download_file(url: str, dest: Path) -> bool:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20, stream=True)
        if resp.status_code != 200:
            return False
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        return True
    except Exception:
        return False


def download_article(session, article, site_name: str) -> dict:
    from db import crud
    folder = article_folder(site_name, article.url)
    images = crud.get_images_for_article(session, article.id)
    ok = skip = fail = 0

    for img in images:
        if img.downloaded:
            skip += 1; continue
        dest = folder / img.filename
        if dest.exists():
            crud.mark_image_downloaded(session, img.id, relative_path(folder, img.filename))
            skip += 1; continue
        if _download_file(img.url, dest):
            crud.mark_image_downloaded(session, img.id, relative_path(folder, img.filename))
            ok += 1
        else:
            fail += 1
        time.sleep(0.3)

    cover_local = ""
    if article.cover_url and not article.cover_local:
        dest = folder / "cover.jpg"
        if dest.exists():
            cover_local = relative_path(folder, "cover.jpg")
        elif _download_file(article.cover_url, dest):
            cover_local = relative_path(folder, "cover.jpg")

    crud.mark_article_downloaded(session, article.id, cover_local)
    return {"ok": ok, "skipped": skip, "failed": fail, "folder": str(folder)}


def build_zip(session, article, site_name: str) -> bytes:
    download_article(session, article, site_name)
    from db import crud
    folder = article_folder(site_name, article.url)
    buf    = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        cover = folder / "cover.jpg"
        if cover.exists():
            zf.write(cover, "cover.jpg")
        for img in crud.get_images_for_article(session, article.id):
            dest = folder / img.filename
            if dest.exists():
                zf.write(dest, img.filename)
    buf.seek(0)
    return buf.read()


def build_zip_bulk(session, articles: list, site_name: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for article in articles:
            from db import crud
            download_article(session, article, site_name)
            folder = article_folder(site_name, article.url)
            slug   = folder.name
            cover  = folder / "cover.jpg"
            if cover.exists():
                zf.write(cover, f"{slug}/cover.jpg")
            for img in crud.get_images_for_article(session, article.id):
                dest = folder / img.filename
                if dest.exists():
                    zf.write(dest, f"{slug}/{img.filename}")
    buf.seek(0)
    return buf.read()
