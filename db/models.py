"""
Modelos SQLModel — partilhados entre crawler e web.
"""

from datetime import datetime
from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel


# ── Tabelas de associação many-to-many ────────────────────────────────────────

class ArticleTag(SQLModel, table=True):
    __tablename__ = "article_tags"
    article_id: int = Field(foreign_key="articles.id", primary_key=True)
    tag_id:     int = Field(foreign_key="tags.id",     primary_key=True)


class ArticleCategory(SQLModel, table=True):
    __tablename__ = "article_categories"
    article_id:  int = Field(foreign_key="articles.id",   primary_key=True)
    category_id: int = Field(foreign_key="categories.id", primary_key=True)


# ── Modelos principais ────────────────────────────────────────────────────────

class Site(SQLModel, table=True):
    __tablename__ = "sites"
    id:       Optional[int] = Field(default=None, primary_key=True)
    key:      str = Field(unique=True, index=True)
    name:     str
    label:    str
    base_url: str

    # Relationships — back_populates deve corresponder exactamente
    # ao nome do atributo do lado oposto
    articles:      List["Article"]     = Relationship(back_populates="site")
    tags:          List["Tag"]         = Relationship(back_populates="site")
    categories:    List["Category"]    = Relationship(back_populates="site")
    listing_pages: List["ListingPage"] = Relationship(back_populates="site")


class Tag(SQLModel, table=True):
    __tablename__ = "tags"
    id:      Optional[int] = Field(default=None, primary_key=True)
    name:    str
    url:     str = Field(unique=True, index=True)
    site_id: int = Field(foreign_key="sites.id")

    site: Optional["Site"] = Relationship(back_populates="tags")
    # Many-to-many com Article — sem back_populates (evita conflito)
    articles: List["Article"] = Relationship(link_model=ArticleTag)


class Category(SQLModel, table=True):
    __tablename__ = "categories"
    id:      Optional[int] = Field(default=None, primary_key=True)
    name:    str
    url:     str = Field(unique=True, index=True)
    site_id: int = Field(foreign_key="sites.id")

    site: Optional["Site"] = Relationship(back_populates="categories")
    # Many-to-many com Article — sem back_populates
    articles: List["Article"] = Relationship(link_model=ArticleCategory)


class Article(SQLModel, table=True):
    __tablename__ = "articles"
    id:                Optional[int] = Field(default=None, primary_key=True)
    url:               str = Field(unique=True, index=True)
    title:             str = Field(default="")
    summary:           str = Field(default="")
    cover_url:         str = Field(default="")
    cover_local:       str = Field(default="")
    total_images:      int = Field(default=0)
    images_downloaded: int = Field(default=0)
    site_id:           int = Field(foreign_key="sites.id")
    scraped_at:        Optional[datetime] = Field(default=None)
    downloaded_at:     Optional[datetime] = Field(default=None)

    site:       Optional["Site"]   = Relationship(back_populates="articles")
    images:     List["Image"]      = Relationship(back_populates="article")
    # Many-to-many — sem back_populates do lado Article
    tags:       List["Tag"]        = Relationship(link_model=ArticleTag)
    categories: List["Category"]   = Relationship(link_model=ArticleCategory)


class Image(SQLModel, table=True):
    __tablename__ = "images"
    id:         Optional[int] = Field(default=None, primary_key=True)
    url:        str = Field(index=True)
    filename:   str = Field(default="")
    local_path: str = Field(default="")
    downloaded: bool = Field(default=False)
    article_id: int = Field(foreign_key="articles.id")

    article: Optional["Article"] = Relationship(back_populates="images")


class ListingPage(SQLModel, table=True):
    __tablename__  = "listing_pages"
    id:            Optional[int] = Field(default=None, primary_key=True)
    url:           str = Field(unique=True, index=True)
    page_type:     str = Field(default="index")
    label:         str = Field(default="")
    site_id:       int = Field(foreign_key="sites.id")
    crawled_at:    Optional[datetime] = Field(default=None)
    article_count: int = Field(default=0)

    # Relationship de volta para Site (obrigatório porque Site.listing_pages existe)
    site: Optional["Site"] = Relationship(back_populates="listing_pages")


class CrawlerJob(SQLModel, table=True):
    __tablename__    = "crawler_jobs"
    id:              Optional[int] = Field(default=None, primary_key=True)
    site_key:        str = Field(index=True)
    status:          str = Field(default="idle")
    pid:             Optional[int] = Field(default=None)
    jobdir:          str = Field(default="")
    started_at:      Optional[datetime] = Field(default=None)
    ended_at:        Optional[datetime] = Field(default=None)
    pages_crawled:   int = Field(default=0)
    articles_found:  int = Field(default=0)
    articles_saved:  int = Field(default=0)
    error_msg:       str = Field(default="")
