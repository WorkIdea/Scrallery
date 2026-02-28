"""
CRUD — todas as operações de BD com deduplicação.
"""

from datetime import datetime
from sqlmodel import Session, select, or_, func, col

from .models import (
    Article, ArticleCategory, ArticleTag,
    Category, CrawlerJob, Image, ListingPage, Site, Tag,
)


# ── Sites ─────────────────────────────────────────────────────────────────────

def get_or_create_site(s: Session, key: str, name: str, label: str, base_url: str) -> Site:
    site = s.exec(select(Site).where(Site.key == key)).first()
    if not site:
        site = Site(key=key, name=name, label=label, base_url=base_url)
        s.add(site); s.commit(); s.refresh(site)
    return site

def get_site(s: Session, key: str) -> Site | None:
    return s.exec(select(Site).where(Site.key == key)).first()

def get_all_sites(s: Session) -> list[Site]:
    return list(s.exec(select(Site)).all())


# ── Listing pages ─────────────────────────────────────────────────────────────

def get_or_create_listing(s: Session, url: str, site_id: int,
                          page_type: str = "index", label: str = "") -> tuple[ListingPage, bool]:
    existing = s.exec(select(ListingPage).where(ListingPage.url == url)).first()
    if existing:
        return existing, False
    page = ListingPage(url=url, site_id=site_id, page_type=page_type, label=label)
    s.add(page); s.commit(); s.refresh(page)
    return page, True

def mark_listing_crawled(s: Session, url: str, article_count: int = 0):
    page = s.exec(select(ListingPage).where(ListingPage.url == url)).first()
    if page:
        page.crawled_at    = datetime.now()
        page.article_count = article_count
        s.add(page); s.commit()

def get_listings_by_site(s: Session, site_id: int) -> list[ListingPage]:
    return list(s.exec(select(ListingPage).where(ListingPage.site_id == site_id)).all())


# ── Tags e Categorias ─────────────────────────────────────────────────────────

def get_or_create_tag(s: Session, name: str, url: str, site_id: int) -> Tag:
    tag = s.exec(select(Tag).where(Tag.url == url)).first()
    if not tag:
        tag = Tag(name=name, url=url, site_id=site_id)
        s.add(tag); s.commit(); s.refresh(tag)
    return tag

def get_or_create_category(s: Session, name: str, url: str, site_id: int) -> Category:
    cat = s.exec(select(Category).where(Category.url == url)).first()
    if not cat:
        cat = Category(name=name, url=url, site_id=site_id)
        s.add(cat); s.commit(); s.refresh(cat)
    return cat

def get_tags_by_site(s: Session, site_id: int) -> list[Tag]:
    return list(s.exec(select(Tag).where(Tag.site_id == site_id)
                       .order_by(Tag.name)).all())

def get_categories_by_site(s: Session, site_id: int) -> list[Category]:
    return list(s.exec(select(Category).where(Category.site_id == site_id)
                       .order_by(Category.name)).all())


# ── Artigos ───────────────────────────────────────────────────────────────────

def get_article(s: Session, url: str) -> Article | None:
    return s.exec(select(Article).where(Article.url == url)).first()

def get_article_by_id(s: Session, article_id: int) -> Article | None:
    return s.get(Article, article_id)

def upsert_article(s: Session, data: dict, site_id: int) -> tuple[Article, bool]:
    url     = data["url"]
    article = s.exec(select(Article).where(Article.url == url)).first()
    created = False

    if not article:
        article = Article(
            url=url, site_id=site_id,
            title=data.get("title", ""),
            summary=data.get("summary", ""),
            cover_url=data.get("cover", ""),
            total_images=data.get("total_images", 0),
            scraped_at=datetime.now(),
        )
        s.add(article); s.commit(); s.refresh(article)
        created = True
    else:
        article.title        = data.get("title")        or article.title
        article.summary      = data.get("summary")      or article.summary
        article.cover_url    = data.get("cover")        or article.cover_url
        article.total_images = data.get("total_images") or article.total_images
        article.scraped_at   = datetime.now()
        s.add(article); s.commit()

    # Tags
    for t in data.get("tags", []):
        tag = get_or_create_tag(s, t["name"], t["url"], site_id)
        if not s.exec(select(ArticleTag).where(
            ArticleTag.article_id == article.id, ArticleTag.tag_id == tag.id
        )).first():
            s.add(ArticleTag(article_id=article.id, tag_id=tag.id))

    # Categorias
    for c in data.get("categories", []):
        cat = get_or_create_category(s, c["name"], c["url"], site_id)
        if not s.exec(select(ArticleCategory).where(
            ArticleCategory.article_id == article.id, ArticleCategory.category_id == cat.id
        )).first():
            s.add(ArticleCategory(article_id=article.id, category_id=cat.id))

    # Imagens
    existing_urls = {i.url for i in s.exec(
        select(Image).where(Image.article_id == article.id)
    ).all()}
    for img_url in data.get("images", []):
        if img_url not in existing_urls:
            s.add(Image(url=img_url, filename=img_url.split("/")[-1],
                        article_id=article.id, downloaded=False))

    s.commit(); s.refresh(article)
    return article, created


def get_articles_by_site(s: Session, site_id: int,
                         limit: int = 50, offset: int = 0,
                         search: str = "",
                         tag_id: int = None,
                         category_id: int = None,
                         sort: str = "recent",
                         downloaded_only: bool = False) -> list[Article]:
    """
    Lista artigos com filtros:
      search         — texto no título ou resumo
      tag_id         — filtrar por tag
      category_id    — filtrar por categoria
      sort           — 'recent' | 'oldest' | 'images' | 'title'
      downloaded_only — só artigos com imagens baixadas
    """
    q = select(Article).where(Article.site_id == site_id)

    if search:
        q = q.where(
            or_(
                col(Article.title).contains(search),
                col(Article.summary).contains(search),
            )
        )

    if tag_id:
        q = q.join(ArticleTag).where(ArticleTag.tag_id == tag_id)

    if category_id:
        q = q.join(ArticleCategory).where(ArticleCategory.category_id == category_id)

    if downloaded_only:
        q = q.where(Article.downloaded_at.isnot(None))

    if sort == "recent":
        q = q.order_by(Article.scraped_at.desc())
    elif sort == "oldest":
        q = q.order_by(Article.scraped_at.asc())
    elif sort == "images":
        q = q.order_by(Article.total_images.desc())
    elif sort == "title":
        q = q.order_by(Article.title.asc())

    return list(s.exec(q.limit(limit).offset(offset)).all())


def count_articles_filtered(s: Session, site_id: int,
                             search: str = "", tag_id: int = None,
                             category_id: int = None,
                             downloaded_only: bool = False) -> int:
    q = select(func.count(Article.id)).where(Article.site_id == site_id)
    if search:
        q = q.where(or_(
            col(Article.title).contains(search),
            col(Article.summary).contains(search),
        ))
    if tag_id:
        q = q.join(ArticleTag).where(ArticleTag.tag_id == tag_id)
    if category_id:
        q = q.join(ArticleCategory).where(ArticleCategory.category_id == category_id)
    if downloaded_only:
        q = q.where(Article.downloaded_at.isnot(None))
    return s.exec(q).one()


def count_articles(s: Session, site_id: int) -> int:
    return s.exec(select(func.count(Article.id)).where(Article.site_id == site_id)).one()


def get_related_by_tag(s: Session, article_id: int, limit: int = 20) -> list[Article]:
    """
    Artigos que partilham pelo menos uma tag com o artigo dado.
    Ordenados pelo número de tags em comum (mais relacionados primeiro).
    Usado para mostrar 'Outros capítulos desta história'.
    """
    # Tags do artigo actual
    article_tags = s.exec(
        select(ArticleTag.tag_id).where(ArticleTag.article_id == article_id)
    ).all()

    if not article_tags:
        return []

    tag_ids = [t for t in article_tags]

    # Artigos que têm essas tags, excluindo o próprio
    related_ids_q = (
        select(ArticleTag.article_id, func.count(ArticleTag.tag_id).label("common_tags"))
        .where(
            ArticleTag.tag_id.in_(tag_ids),
            ArticleTag.article_id != article_id,
        )
        .group_by(ArticleTag.article_id)
        .order_by(func.count(ArticleTag.tag_id).desc())
        .limit(limit)
    )
    rows = s.exec(related_ids_q).all()
    if not rows:
        return []

    ids = [r[0] for r in rows]
    articles = {a.id: a for a in s.exec(
        select(Article).where(Article.id.in_(ids))
    ).all()}
    # Preserva ordem por relevância
    return [articles[i] for i in ids if i in articles]


# ── Imagens ───────────────────────────────────────────────────────────────────

def get_images_for_article(s: Session, article_id: int) -> list[Image]:
    return list(s.exec(select(Image).where(Image.article_id == article_id)).all())

def get_pending_images(s: Session, article_id: int) -> list[Image]:
    return list(s.exec(select(Image).where(
        Image.article_id == article_id, Image.downloaded == False
    )).all())

def mark_image_downloaded(s: Session, image_id: int, local_path: str):
    img = s.get(Image, image_id)
    if img:
        img.downloaded = True
        img.local_path = local_path
        s.add(img); s.commit()

def mark_article_downloaded(s: Session, article_id: int, cover_local: str = ""):
    article = s.get(Article, article_id)
    if article:
        article.downloaded_at     = datetime.now()
        article.images_downloaded = len(get_images_for_article(s, article_id))
        if cover_local:
            article.cover_local = cover_local
        s.add(article); s.commit()


# ── CrawlerJob ────────────────────────────────────────────────────────────────

def get_latest_job(s: Session, site_key: str) -> CrawlerJob | None:
    return s.exec(
        select(CrawlerJob).where(CrawlerJob.site_key == site_key)
        .order_by(CrawlerJob.id.desc())
    ).first()

def create_job(s: Session, site_key: str, jobdir: str) -> CrawlerJob:
    job = CrawlerJob(site_key=site_key, status="running",
                     jobdir=jobdir, started_at=datetime.now())
    s.add(job); s.commit(); s.refresh(job)
    return job

def update_job(s: Session, job_id: int, **kwargs):
    job = s.get(CrawlerJob, job_id)
    if job:
        for k, v in kwargs.items():
            setattr(job, k, v)
        s.add(job); s.commit()


# ── Estatísticas gerais ───────────────────────────────────────────────────────

def get_stats(s: Session, site_id: int) -> dict:
    total_articles   = count_articles(s, site_id)
    total_images     = s.exec(
        select(func.count(Image.id))
        .join(Article)
        .where(Article.site_id == site_id)
    ).one()
    downloaded_imgs  = s.exec(
        select(func.count(Image.id))
        .join(Article)
        .where(Article.site_id == site_id, Image.downloaded == True)
    ).one()
    downloaded_arts  = s.exec(
        select(func.count(Article.id))
        .where(Article.site_id == site_id, Article.downloaded_at.isnot(None))
    ).one()
    total_tags       = s.exec(
        select(func.count(Tag.id)).where(Tag.site_id == site_id)
    ).one()

    return {
        "total_articles":  total_articles,
        "total_images":    total_images,
        "downloaded_imgs": downloaded_imgs,
        "downloaded_arts": downloaded_arts,
        "total_tags":      total_tags,
        "pct_downloaded":  int((downloaded_imgs / total_images * 100) if total_images else 0),
    }
