"""
Static Site Generator for Netlify Deployment
Converts the Flask/Jinja2 templates into static HTML files in `dist/`.

Dynamic data (site settings + projects) is pulled from Supabase at build time,
exactly like the live Flask app. Set SUPABASE_URL / SUPABASE_KEY / SUPABASE_BUCKET
as Netlify environment variables (or in a local .env) so the build can read them.
If Supabase is unavailable, the build still succeeds: settings fall back to
defaults and the portfolio is rendered empty.
"""

import os
import shutil
from datetime import datetime

from jinja2 import Environment, FileSystemLoader

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import supabase_service as db

# Configuration
TEMPLATE_DIR = "templates"
STATIC_DIR = "static"
OUTPUT_DIR = "dist"

# Static pages: (template_name, output_path, endpoint)
PAGES = [
    ("home.html", "index.html", "home"),
    ("about.html", "about/index.html", "about"),
    ("contact.html", "contact/index.html", "contact"),
    ("services.html", "services/index.html", "services"),
    ("thank-you.html", "thank-you/index.html", "thank_you"),
]

# Legacy project URLs → the seeded dynamic slugs (keeps old links alive).
LEGACY_PROJECT_REDIRECTS = {
    "seo_helper_master": "seo-master",
    "time_center": "time-center-ecommerce",
}


def make_url_for():
    """Return a url_for() that mimics Flask's, including project_detail(slug)."""
    url_map = {
        "home": "/",
        "about": "/about",
        "contact": "/contact",
        "services": "/services",
        "portfolio": "/portfolio",
        "thank_you": "/thank-you",
        # Admin has no static export; link back to the (server-hosted) admin.
        "admin_dashboard": "/admin",
    }

    def url_for(endpoint, **kwargs):
        if endpoint == "static":
            return f"/static/{kwargs.get('filename', '')}"
        if endpoint == "project_detail":
            return f"/project/{kwargs.get('slug', '')}"
        return url_map.get(endpoint, "/")

    return url_for


class MockRequest:
    """Mock Flask's request object (only .endpoint is used in templates)."""
    def __init__(self, endpoint):
        self.endpoint = endpoint


def build_site():
    """Build the static site into OUTPUT_DIR."""

    # Clean and recreate the output directory.
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    # Copy static assets.
    shutil.copytree(STATIC_DIR, os.path.join(OUTPUT_DIR, "static"))
    print(f"Copied static files to {OUTPUT_DIR}/static")

    # Copy _redirects to the dist root if present.
    redirects_src = os.path.join(STATIC_DIR, "_redirects")
    if os.path.exists(redirects_src):
        shutil.copy(redirects_src, os.path.join(OUTPUT_DIR, "_redirects"))
        print("Copied _redirects to dist root")

    # Pull dynamic data from Supabase (falls back gracefully if unconfigured).
    if not db.is_configured():
        print(f"WARNING: Supabase not configured ({db.config_error()}). "
              "Rendering with default settings and no projects.")
    settings = db.get_settings()
    projects = db.list_projects()
    print(f"Loaded {len(projects)} project(s) from Supabase")

    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    url_for = make_url_for()

    # Context shared by every page (mirrors the Flask context processor).
    base_context = {
        "url_for": url_for,
        "settings": settings,
        "current_year": datetime.now().year,
        "get_flashed_messages": lambda with_categories=False: [],
        # Marks this as the static export so templates can hide server-only
        # features (e.g. the Admin link, which has no static route).
        "is_static_build": True,
    }

    def render(template_name, output_path, endpoint, **extra):
        template = env.get_template(template_name)
        html = template.render(
            request=MockRequest(endpoint), **base_context, **extra
        )
        full_path = os.path.join(OUTPUT_DIR, output_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Generated: {output_path}")

    # 1) Static pages.
    for template_name, output_path, endpoint in PAGES:
        render(template_name, output_path, endpoint)

    # 2) Portfolio listing (needs the projects list).
    render("portfolio.html", "portfolio/index.html", "portfolio", projects=projects)

    # 3) One detail page per project at /project/<slug>/index.html.
    for project in projects:
        slug = project.get("slug")
        if not slug:
            continue
        render(
            "project_detail.html",
            f"project/{slug}/index.html",
            "project_detail",
            project=project,
        )

    # 4) Legacy project URLs → redirect stubs to the new slugs.
    for legacy_path, slug in LEGACY_PROJECT_REDIRECTS.items():
        _write_redirect_stub(legacy_path, f"/project/{slug}")

    print(f"\nBuild complete! Output in '{OUTPUT_DIR}' directory")


def _write_redirect_stub(legacy_path, target):
    """Emit a tiny HTML page that redirects an old URL to its new location."""
    out = os.path.join(OUTPUT_DIR, legacy_path, "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    html = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<meta http-equiv='refresh' content='0; url={target}'>"
        f"<link rel='canonical' href='{target}'>"
        f"<title>Redirecting…</title></head>"
        f"<body>Redirecting to <a href='{target}'>{target}</a>.</body></html>"
    )
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Generated redirect: /{legacy_path} -> {target}")


if __name__ == "__main__":
    build_site()
