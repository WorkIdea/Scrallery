"""
Flask application factory.
"""

import os
from pathlib import Path

from flask import Flask, send_from_directory

from db.database import init_db
from .routes.dashboard import bp as bp_dashboard
from .routes.browse    import bp as bp_browse
from .routes.article   import bp as bp_article
from .routes.download  import bp as bp_download
from .routes.library   import bp as bp_library

ROOT = Path(__file__).parent.parent.parent


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent / "templates"),
        static_folder=str(Path(__file__).parent / "static"),
    )

    init_db()

    app.register_blueprint(bp_dashboard)
    app.register_blueprint(bp_browse)
    app.register_blueprint(bp_article)
    app.register_blueprint(bp_download)
    app.register_blueprint(bp_library)

    downloads_dir = Path(os.environ.get("DOWNLOADS_ROOT", str(ROOT / "downloads")))
    downloads_dir.mkdir(parents=True, exist_ok=True)

    @app.route("/downloads/<path:filename>")
    def serve_download(filename):
        return send_from_directory(str(downloads_dir), filename)

    return app
