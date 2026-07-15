<div align="center">

<img src="static/images/Testing.jpg" alt="SQA Portfolio logo" width="120" height="120" />

# Muhammad Taha Khurram — QA Engineer Portfolio

**Quality engineering that drives excellence.**

A professional portfolio website showcasing expertise in Software Quality Assurance — manual testing, automation, API & performance testing, and QA consultation — with a built-in admin portal for managing projects and contact details.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-app-000000?logo=flask&logoColor=white)
![Jinja2](https://img.shields.io/badge/Jinja2-templating-B41717?logo=jinja&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-Postgres%20%2B%20Storage-3ECF8E?logo=supabase&logoColor=white)
![HTML5](https://img.shields.io/badge/HTML5-markup-E34F26?logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-styling-1572B6?logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-ES6-F7DF1E?logo=javascript&logoColor=black)
![Netlify](https://img.shields.io/badge/Netlify-static-00C7B7?logo=netlify&logoColor=white)
![License](https://img.shields.io/badge/License-Proprietary-red)

**live** [mtahalabs.netlify.app](https://mtahalabs.netlify.app)

</div>

---

## ✨ Highlights

- 🧪 **Five QA services** — Manual Testing, Automation Testing, API Testing, Performance Testing, and Security Testing, each with a dedicated breakdown.
- 👤 **Full portfolio experience** — Home, About, Services, Portfolio, and Contact pages sharing a consistent navbar, header, and footer.
- 📈 **Proven results** — headline metrics (15+ projects, 3K+ test cases, 85% automation coverage, 95% defect detection) surfaced on the Services page.
- 🗂️ **Dynamic project showcase** — case studies are stored in Supabase and rendered on their own `/project/<slug>` routes, with per-project image galleries.
- 💬 **Editable testimonials** — the "What Clients Say" cards on the home page are managed from the admin panel (add / edit / delete / order).
- 💼 **LinkedIn-style experience** — the About-page experience timeline is fully editable, with a date-range picker for the time period and automatic grouping of multiple roles at the same company into one card.
- 🔐 **Admin portal** — a password-protected `/admin` dashboard to manage projects, testimonials, and experience entries, upload images, and edit contact details — no code changes needed.
- 📬 **Working contact form** — server-side validated form wired to email via Flask-Mail (Mailtrap SMTP), with a dedicated thank-you page.
- 🛟 **Graceful degradation** — if Supabase isn't configured, the public site still runs on sensible defaults instead of crashing.
- ⚙️ **Static-site pipeline** — a `build.py` generator renders the Jinja2 templates to plain HTML in `dist/` for Netlify, mocking Flask's `url_for`/`request` so templates stay portable.
- 🚀 **One-command deploy** — Netlify runs `python build.py`, publishes `dist/`, and applies clean-URL redirects plus caching & security headers.

## 🛠️ Tech Stack

- **Frontend:** HTML5, CSS3, JavaScript (per-page CSS/JS modules), design tokens in `static/css/tokens.css`
- **Templating:** Jinja2 (shared `partials/` for header, navbar, footer)
- **Backend:** Flask + Flask-Mail (routes, admin portal, contact form)
- **Database & Storage:** Supabase (Postgres for projects, testimonials, experiences & settings, Storage bucket for images)
- **Auth:** Flask session + Werkzeug password hashing (single admin)
- **Build:** `build.py` static site generator → `dist/`
- **Deployment:** Netlify (static export) · Gunicorn `Procfile` for full server hosting

## 📁 Project Structure

```
SQA_Portfolio/
├── templates/                 # Jinja2 HTML templates
│   ├── partials/              # Reusable components (header, navbar, footer)
│   ├── admin/                 # Admin portal (dashboard, project/testimonial/experience & settings forms)
│   ├── home.html
│   ├── about.html
│   ├── services.html
│   ├── portfolio.html
│   ├── project_detail.html    # Dynamic project page (/project/<slug>)
│   ├── contact.html
│   └── thank-you.html
├── static/
│   ├── css/                   # Per-page stylesheets + tokens.css
│   ├── js/                    # Per-page scripts + loader
│   ├── images/                # Images and assets
│   ├── files/                 # Downloadable CV
│   └── _redirects             # Netlify redirects
├── app.py                     # Flask app (public routes, admin routes, contact form)
├── auth.py                    # Admin authentication (session + password hash)
├── supabase_service.py        # Data layer — the only module that talks to Supabase
├── supabase_schema.sql        # Database schema (projects, testimonials, experiences, settings) + storage bucket
├── migrate.py                 # One-off DB migrations (gallery_urls column, testimonials & experiences tables)
├── build.py                   # Static site generator
├── netlify.toml               # Netlify build config, redirects & headers
├── Procfile                   # Gunicorn entry (server hosting)
├── requirements.txt           # Python dependencies
├── runtime.txt                # Python version (3.11)
├── .env.example               # Environment variable template
└── LICENSE                    # Proprietary license
```

## ⚙️ Configuration

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Flask session signing key (use a long random string). |
| `ADMIN_USERNAME` | Admin login username (default `admin`). |
| `ADMIN_PASSWORD_HASH` | Werkzeug password hash for the admin (preferred). |
| `ADMIN_PASSWORD` | Plaintext password — dev-only fallback if no hash is set. |
| `SUPABASE_URL` | Your Supabase project URL. |
| `SUPABASE_KEY` | Supabase **service-role** key (server-side only; bypasses RLS). |
| `SUPABASE_BUCKET` | Public storage bucket for project images (`project-images`). |
| `MAIL_*` | Mailtrap SMTP settings for the contact form. |

Generate an admin password hash with:

```bash
python -c "from werkzeug.security import generate_password_hash as g; print(g('yourpassword'))"
```

### Supabase setup

1. Create a project at [supabase.com](https://supabase.com).
2. Open **SQL Editor** and run [`supabase_schema.sql`](supabase_schema.sql) — it creates the `projects`, `testimonials`, `experiences`, and `settings` tables and the public `project-images` storage bucket.
3. Copy your project URL and **service-role** key (Project Settings → API) into `.env`.

## 💻 Local Development

**Option A — run the Flask app (admin portal + live contact form):**

```bash
git clone https://github.com/mtahaofficial007-collab/SQA_Portfolio.git
cd SQA_Portfolio

python -m venv venv
# Windows:  .\venv\Scripts\Activate.ps1
# macOS/Linux:  source venv/bin/activate

pip install -r requirements.txt
python app.py
# open http://127.0.0.1:5000  ·  admin at http://127.0.0.1:5000/admin
```

> Log in to `/admin`, then use **Seed starter projects** on the dashboard to load the initial case studies.

**Option B — build the static site (Netlify export):**

```bash
pip install -r requirements.txt
python build.py
cd dist && python -m http.server 8000
# open http://localhost:8000
```

## 🗄️ Database Migrations

Schema changes are additive and idempotent. To apply pending migrations
against an existing database — the multi-image `gallery_urls` column and the
`testimonials` / `experiences` tables — set `SUPABASE_DB_URL` (the Postgres
connection URI from Supabase → Project Settings → Database) in `.env` and run:

```bash
python migrate.py
```

## 🚀 Deployment

Configured for automatic deployment on Netlify (static export):

1. Push changes to the `main` branch.
2. Netlify runs `python build.py`.
3. The `dist/` folder is published, with clean-URL redirects and caching/security headers applied via `netlify.toml`.

For full server-side hosting (live contact form + admin portal), deploy the
Flask app with the included `Procfile` (`gunicorn app:app`) on a platform such
as Railway or Render, and set the environment variables from `.env`.

## 📇 Contact

- **Email:** tahakhurramofficial@gmail.com
- **LinkedIn:** [Muhammad Taha Khurram](https://www.linkedin.com/in/muhammad-taha-khurram-2b77ba366/)
- **GitHub:** [mtahaofficial007-collab](https://github.com/Taha-Khurram)

## 📄 License

**Proprietary — © 2025–2026 Muhammad Taha Khurram. All Rights Reserved.**

This project is made publicly viewable for demonstration and portfolio review
only. It may not be used, copied, modified, or redistributed without explicit
written permission. See the [LICENSE](LICENSE) file for the full terms.
