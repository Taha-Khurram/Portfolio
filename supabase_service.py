"""
Supabase (Postgres + Storage) data layer for the portfolio.

This is the ONLY module that talks to Supabase. Everything else calls the
functions below. If Supabase is not configured (no credentials in the
environment) the app still runs: settings fall back to sensible defaults and
the project list is empty, so the public site never crashes. Admin writes,
however, require a configured Supabase project.

Expected database objects (see supabase_schema.sql):
  - table `settings`  : single row keyed id='site'
  - table `projects`  : one row per project
  - storage bucket    : public bucket for uploaded project images
"""

import os
import re
import uuid
from datetime import datetime, timezone

# supabase is optional at import time so the site can boot without it.
try:
    from supabase import create_client, Client  # noqa: F401
    _SUPABASE_IMPORTED = True
except ImportError:  # pragma: no cover - only when dependency missing
    _SUPABASE_IMPORTED = False


# ------------------------------------------------------------------
# Defaults — used when the settings row does not exist yet, or when
# Supabase is not configured at all. These match the site's original
# hardcoded values so nothing looks broken on first run.
# ------------------------------------------------------------------
DEFAULT_SETTINGS = {
    "email": "m.tahaofficial007@gmail.com",
    "phone": "+92 331 5604180",
    "linkedin_url": "https://www.linkedin.com/in/muhammad-taha-khurram-2b77ba366/",
    "github_url": "https://github.com/mtahaofficial007-collab",
}

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

SETTINGS_ROW_ID = "site"

# ------------------------------------------------------------------
# Fallback content — mirrors the site's original hardcoded cards so
# the public pages are never empty (before any admin edits, or when
# Supabase isn't configured / the tables aren't migrated yet).
# ------------------------------------------------------------------
DEFAULT_TESTIMONIALS = [
    {
        "quote": "Working with Muhammad Taha Khurram was a game-changer for our QA processes. His meticulous attention to detail and automation expertise improved our software reliability dramatically. Highly recommend for any project requiring top-notch QA!",
        "name": "Momentum",
        "role": "CEO, Momentum",
    },
    {
        "quote": "Muhammad Taha's QA services transformed the way we approach quality. From manual testing to automation, his skills ensured our releases were always flawless. Our SEO tools now perform seamlessly thanks to his testing expertise!",
        "name": "SEO For Purpose",
        "role": "Founder, SEO For Purpose",
    },
    {
        "quote": "The dedication and professionalism shown by Muhammad Taha Khurram in our projects was outstanding. He delivered thorough testing and clear reports that helped us enhance product quality and user experience significantly.",
        "name": "Meeha",
        "role": "Product Manager, Meeha",
    },
]

DEFAULT_EXPERIENCES = [
    {
        "title": "QA Engineer",
        "company": "Meeha — Lahore, Pakistan",
        "period": "2024 – Present",
        "bullets": [
            "Developed and managed QA process for an AI-driven application optimizing website content for SEO.",
            "Designed and executed test plans for functional, regression, and performance testing.",
            "Authored automated UI workflows using Selenium for cross-browser testing.",
            "Conducted API testing with Postman, ensuring data integrity and error handling.",
            "Provided feedback to improve AI recommendations and application functionality.",
            "Actively participated in Agile ceremonies (sprint planning, daily stand-ups).",
        ],
        "reference_url": "",
    },
]

_client = None        # Supabase client (lazily created)
_bucket = None        # Storage bucket name
_init_attempted = False
_init_error = None


# ------------------------------------------------------------------
# Initialisation
# ------------------------------------------------------------------
def _init():
    """Initialise the Supabase client once. Safe to call repeatedly."""
    global _client, _bucket, _init_attempted, _init_error

    if _init_attempted:
        return _client is not None

    _init_attempted = True

    if not _SUPABASE_IMPORTED:
        _init_error = "supabase package is not installed."
        return False

    url = os.getenv("SUPABASE_URL")
    # Prefer the service-role key so admin writes/uploads bypass RLS.
    key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    _bucket = os.getenv("SUPABASE_BUCKET", "project-images")

    if not url or not key:
        _init_error = "SUPABASE_URL and SUPABASE_KEY env vars must be set."
        return False

    try:
        _client = create_client(url, key)
        return True
    except Exception as exc:  # pragma: no cover - config errors
        _init_error = f"Supabase init failed: {exc}"
        _client = None
        return False


def is_configured():
    """True when the Supabase client is ready (credentials present and valid)."""
    return _init()


def config_error():
    """Human-readable reason Supabase is unavailable, or None."""
    return _init_error


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def slugify(text):
    """Turn a title into a URL-safe slug."""
    text = (text or "").strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-") or "project"


def _unique_slug(base_slug, exclude_id=None):
    """Ensure the slug is unique across the projects table."""
    if not _init():
        return base_slug
    slug = base_slug
    n = 2
    while True:
        try:
            resp = _client.table("projects").select("id").eq("slug", slug).execute()
            rows = resp.data or []
        except Exception:
            return slug
        clash = any(str(r.get("id")) != str(exclude_id) for r in rows)
        if not clash:
            return slug
        slug = f"{base_slug}-{n}"
        n += 1


# ------------------------------------------------------------------
# Settings
# ------------------------------------------------------------------
# Short-lived in-process cache. get_settings() is called on EVERY request
# (via the template context processor), so hitting Supabase each time adds
# network latency to every page. Cache for a minute and invalidate on write.
import time  # noqa: E402  (kept next to its only user)

_settings_cache = {"data": None, "ts": 0.0}
_SETTINGS_TTL = 60  # seconds


def get_settings():
    """Return the site settings dict (cached), falling back to defaults."""
    now = time.time()
    if _settings_cache["data"] is not None and now - _settings_cache["ts"] < _SETTINGS_TTL:
        return dict(_settings_cache["data"])

    if not _init():
        return dict(DEFAULT_SETTINGS)
    try:
        resp = (
            _client.table("settings")
            .select("*")
            .eq("id", SETTINGS_ROW_ID)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        if rows:
            data = rows[0] or {}
            data.pop("id", None)
            # Merge over defaults so missing keys are always present.
            merged = {**DEFAULT_SETTINGS, **{k: v for k, v in data.items() if v is not None}}
            _settings_cache["data"] = merged
            _settings_cache["ts"] = now
            return dict(merged)
    except Exception:
        pass
    return dict(DEFAULT_SETTINGS)


def update_settings(data):
    """Persist site settings. Raises if Supabase is not configured."""
    if not _init():
        raise RuntimeError(config_error() or "Supabase is not configured.")
    payload = {
        "id": SETTINGS_ROW_ID,
        "email": (data.get("email") or "").strip(),
        "phone": (data.get("phone") or "").strip(),
        "linkedin_url": (data.get("linkedin_url") or "").strip(),
        "github_url": (data.get("github_url") or "").strip(),
    }
    _client.table("settings").upsert(payload).execute()
    # Invalidate the cache so the change is reflected immediately.
    _settings_cache["data"] = None
    _settings_cache["ts"] = 0.0
    payload.pop("id", None)
    return payload


# ------------------------------------------------------------------
# Projects
# ------------------------------------------------------------------
def _row_to_project(row):
    """Normalise a DB row into the project dict the app/templates expect."""
    data = dict(row or {})
    data["id"] = str(data.get("id"))
    # DB column is `sort_order` (avoids the reserved word `order`); the rest of
    # the app uses `order`, so translate here.
    data["order"] = data.pop("sort_order", 0) or 0
    if not isinstance(data.get("tags"), list):
        data["tags"] = data.get("tags") or []
    if not isinstance(data.get("gallery_urls"), list):
        data["gallery_urls"] = data.get("gallery_urls") or []
    return data


def list_projects():
    """All projects, ordered by `order` then creation time. [] on failure."""
    if not _init():
        return []
    try:
        resp = (
            _client.table("projects")
            .select("*")
            .order("sort_order")
            .order("created_at")
            .execute()
        )
        return [_row_to_project(r) for r in (resp.data or [])]
    except Exception:
        return []


def get_project(slug):
    """Fetch one project by slug, or None."""
    if not _init():
        return None
    try:
        resp = (
            _client.table("projects").select("*").eq("slug", slug).limit(1).execute()
        )
        rows = resp.data or []
        if rows:
            return _row_to_project(rows[0])
    except Exception:
        pass
    return None


def get_project_by_id(project_id):
    if not _init():
        return None
    try:
        resp = (
            _client.table("projects").select("*").eq("id", project_id).limit(1).execute()
        )
        rows = resp.data or []
        if rows:
            return _row_to_project(rows[0])
    except Exception:
        pass
    return None


# Set True after a write had to drop `gallery_urls` because the column is not
# in the database yet. The admin route reads this to warn the user to migrate.
_gallery_column_missing = False


def gallery_column_missing():
    """True if the last write skipped gallery_urls (column not migrated yet)."""
    return _gallery_column_missing


def _is_missing_gallery_error(exc):
    """Detect the PostgREST error raised when `gallery_urls` isn't in the DB."""
    msg = str(exc)
    return "gallery_urls" in msg and (
        "PGRST204" in msg or "schema cache" in msg or "column" in msg
    )


def is_missing_table_error(exc):
    """Detect the PostgREST error raised when a whole table isn't in the DB yet
    (e.g. `testimonials`/`experiences` before the migration has been run)."""
    msg = str(exc)
    return "PGRST205" in msg or "Could not find the table" in msg


def create_project(data):
    """Create a project. Returns the new id."""
    global _gallery_column_missing
    if not _init():
        raise RuntimeError(config_error() or "Supabase is not configured.")
    payload = _clean_project_payload(data)
    payload["slug"] = _unique_slug(slugify(data.get("slug") or data.get("title")))
    payload["created_at"] = datetime.now(timezone.utc).isoformat()
    _gallery_column_missing = False
    try:
        resp = _client.table("projects").insert(payload).execute()
    except Exception as exc:
        # DB not migrated yet: retry without the gallery so the save succeeds.
        if "gallery_urls" in payload and _is_missing_gallery_error(exc):
            payload.pop("gallery_urls", None)
            _gallery_column_missing = True
            resp = _client.table("projects").insert(payload).execute()
        else:
            raise
    rows = resp.data or []
    return str(rows[0]["id"]) if rows else None


def update_project(project_id, data):
    global _gallery_column_missing
    if not _init():
        raise RuntimeError(config_error() or "Supabase is not configured.")
    payload = _clean_project_payload(data)
    if data.get("slug") or data.get("title"):
        payload["slug"] = _unique_slug(
            slugify(data.get("slug") or data.get("title")), exclude_id=project_id
        )
    _gallery_column_missing = False
    try:
        _client.table("projects").update(payload).eq("id", project_id).execute()
    except Exception as exc:
        if "gallery_urls" in payload and _is_missing_gallery_error(exc):
            payload.pop("gallery_urls", None)
            _gallery_column_missing = True
            _client.table("projects").update(payload).eq("id", project_id).execute()
        else:
            raise
    return project_id


def delete_project(project_id):
    if not _init():
        raise RuntimeError(config_error() or "Supabase is not configured.")
    _client.table("projects").delete().eq("id", project_id).execute()


def _clean_project_payload(data):
    """Whitelist + normalise the fields we store for a project."""
    tags = data.get("tags")
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    payload = {
        "title": (data.get("title") or "").strip(),
        "short_description": (data.get("short_description") or "").strip(),
        "overview": (data.get("overview") or "").strip(),
        "tags": tags or [],
    }
    # Only overwrite images when a new URL was provided (edit keeps old image).
    if data.get("card_image_url"):
        payload["card_image_url"] = data["card_image_url"]
    if data.get("preview_image_url"):
        payload["preview_image_url"] = data["preview_image_url"]
    # Gallery is set as a whole list (already merged by the caller), so honour
    # the key whenever it's present — even an empty list, to allow clearing.
    if "gallery_urls" in data:
        gallery = data["gallery_urls"] or []
        payload["gallery_urls"] = [u for u in gallery if u]
    if data.get("order") is not None:
        try:
            payload["sort_order"] = int(data["order"])
        except (TypeError, ValueError):
            payload["sort_order"] = 0
    return payload


# ------------------------------------------------------------------
# Testimonials  ("What Clients Say" cards)
# ------------------------------------------------------------------
def _row_to_testimonial(row):
    data = dict(row or {})
    data["id"] = str(data.get("id"))
    data["order"] = data.pop("sort_order", 0) or 0
    return data


def list_testimonials():
    """All testimonials ordered for display. [] on failure/misconfig."""
    if not _init():
        return []
    try:
        resp = (
            _client.table("testimonials")
            .select("*")
            .order("sort_order")
            .order("created_at")
            .execute()
        )
        return [_row_to_testimonial(r) for r in (resp.data or [])]
    except Exception:
        return []


def get_testimonial_by_id(testimonial_id):
    if not _init():
        return None
    try:
        resp = (
            _client.table("testimonials")
            .select("*")
            .eq("id", testimonial_id)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        if rows:
            return _row_to_testimonial(rows[0])
    except Exception:
        pass
    return None


def _clean_testimonial_payload(data):
    payload = {
        "quote": (data.get("quote") or "").strip(),
        "name": (data.get("name") or "").strip(),
        "role": (data.get("role") or "").strip(),
    }
    if data.get("order") is not None:
        try:
            payload["sort_order"] = int(data["order"])
        except (TypeError, ValueError):
            payload["sort_order"] = 0
    return payload


def create_testimonial(data):
    if not _init():
        raise RuntimeError(config_error() or "Supabase is not configured.")
    payload = _clean_testimonial_payload(data)
    payload["created_at"] = datetime.now(timezone.utc).isoformat()
    resp = _client.table("testimonials").insert(payload).execute()
    rows = resp.data or []
    return str(rows[0]["id"]) if rows else None


def update_testimonial(testimonial_id, data):
    if not _init():
        raise RuntimeError(config_error() or "Supabase is not configured.")
    payload = _clean_testimonial_payload(data)
    _client.table("testimonials").update(payload).eq("id", testimonial_id).execute()
    return testimonial_id


def delete_testimonial(testimonial_id):
    if not _init():
        raise RuntimeError(config_error() or "Supabase is not configured.")
    _client.table("testimonials").delete().eq("id", testimonial_id).execute()


# ------------------------------------------------------------------
# Experiences  (About-page professional timeline)
# ------------------------------------------------------------------
def _row_to_experience(row):
    data = dict(row or {})
    data["id"] = str(data.get("id"))
    data["order"] = data.pop("sort_order", 0) or 0
    if not isinstance(data.get("bullets"), list):
        data["bullets"] = data.get("bullets") or []
    return data


def list_experiences():
    """All experience entries ordered for display. [] on failure/misconfig."""
    if not _init():
        return []
    try:
        resp = (
            _client.table("experiences")
            .select("*")
            .order("sort_order")
            .order("created_at")
            .execute()
        )
        return [_row_to_experience(r) for r in (resp.data or [])]
    except Exception:
        return []


def get_experience_by_id(experience_id):
    if not _init():
        return None
    try:
        resp = (
            _client.table("experiences")
            .select("*")
            .eq("id", experience_id)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        if rows:
            return _row_to_experience(rows[0])
    except Exception:
        pass
    return None


def _clean_experience_payload(data):
    bullets = data.get("bullets")
    if isinstance(bullets, str):
        # One responsibility per line in the admin textarea.
        bullets = [b.strip() for b in bullets.splitlines() if b.strip()]
    payload = {
        "title": (data.get("title") or "").strip(),
        "company": (data.get("company") or "").strip(),
        "period": (data.get("period") or "").strip(),
        "bullets": bullets or [],
        "reference_url": (data.get("reference_url") or "").strip(),
    }
    if data.get("order") is not None:
        try:
            payload["sort_order"] = int(data["order"])
        except (TypeError, ValueError):
            payload["sort_order"] = 0
    return payload


def create_experience(data):
    if not _init():
        raise RuntimeError(config_error() or "Supabase is not configured.")
    payload = _clean_experience_payload(data)
    payload["created_at"] = datetime.now(timezone.utc).isoformat()
    resp = _client.table("experiences").insert(payload).execute()
    rows = resp.data or []
    return str(rows[0]["id"]) if rows else None


def update_experience(experience_id, data):
    if not _init():
        raise RuntimeError(config_error() or "Supabase is not configured.")
    payload = _clean_experience_payload(data)
    _client.table("experiences").update(payload).eq("id", experience_id).execute()
    return experience_id


def delete_experience(experience_id):
    if not _init():
        raise RuntimeError(config_error() or "Supabase is not configured.")
    _client.table("experiences").delete().eq("id", experience_id).execute()


# ------------------------------------------------------------------
# Image upload (Supabase Storage)
# ------------------------------------------------------------------
def allowed_image(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS
    )


def upload_image(file_storage):
    """
    Upload a Werkzeug FileStorage to Supabase Storage and return its public URL.
    Returns None if no file was provided. Raises on misconfig / bad file.
    """
    if file_storage is None or not file_storage.filename:
        return None
    if not _init():
        raise RuntimeError(config_error() or "Supabase is not configured.")
    if not _bucket:
        raise RuntimeError("SUPABASE_BUCKET is not configured.")
    if not allowed_image(file_storage.filename):
        raise ValueError("Unsupported image type.")

    from werkzeug.utils import secure_filename

    safe = secure_filename(file_storage.filename)
    ext = safe.rsplit(".", 1)[1].lower()
    path = f"projects/{uuid.uuid4().hex}.{ext}"

    file_bytes = file_storage.read()
    storage = _client.storage.from_(_bucket)
    storage.upload(
        path,
        file_bytes,
        {"content-type": file_storage.mimetype or "application/octet-stream"},
    )
    # get_public_url returns the fully-qualified public URL for the object.
    return storage.get_public_url(path)


def upload_images(file_list):
    """
    Upload a list of Werkzeug FileStorage objects and return the public URLs.
    Empty/blank entries (e.g. an untouched multi-file input) are skipped.
    Raises on the first bad file / misconfiguration.
    """
    urls = []
    for fs in file_list or []:
        url = upload_image(fs)
        if url:
            urls.append(url)
    return urls
