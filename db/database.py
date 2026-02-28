"""
Engine SQLite.
DB_PATH é configurado via variável de ambiente DATABASE_URL
para funcionar tanto local como em container.
"""

import os
from contextlib import contextmanager
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from .models import (  # noqa: F401 — regista todos os modelos
    Article, ArticleCategory, ArticleTag,
    Category, CrawlerJob, Image, ListingPage, Site, Tag,
)

# Em container: DATABASE_URL=sqlite:////data/crawler.db
# Local: usa crawler.db na pasta raiz do projecto
_default = f"sqlite:///{Path(__file__).parent.parent / 'crawler.db'}"
DATABASE_URL = os.environ.get("DATABASE_URL", _default)

_engine = create_engine(DATABASE_URL, echo=False,
                        connect_args={"check_same_thread": False})


def init_db():
    SQLModel.metadata.create_all(_engine)


def get_session():
    """Gerador para Flask (usado com g ou directly)."""
    with Session(_engine) as session:
        yield session


@contextmanager
def session_ctx():
    """Context manager para uso fora de requests."""
    with Session(_engine) as session:
        yield session
