import os
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, flash, url_for, abort
)
from flask_mail import Mail, Message

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import auth
import supabase_service as db


# ------------------------------------------------------------------
# Flask App Configuration
# ------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-only-change-me")
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # 8 MB upload cap

# Let the browser cache static assets (CSS/JS/images/fonts) for a day so they
# aren't re-fetched on every page navigation. Bump a ?v= query on a file's URL
# if you need to force-refresh it after an edit.
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 86400  # 1 day

# ------------------------------------------------------------------
# Email Configuration (Mailtrap SMTP) — credentials from environment
# ------------------------------------------------------------------
app.config.update(
    MAIL_SERVER=os.getenv("MAIL_SERVER", "sandbox.smtp.mailtrap.io"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", "2525")),
    MAIL_USE_TLS=os.getenv("MAIL_USE_TLS", "true").lower() == "true",
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_DEFAULT_SENDER=(
        os.getenv("MAIL_SENDER_NAME", "Portfolio Contact"),
        os.getenv("MAIL_SENDER_EMAIL", "m.tahaofficial007@gmail.com"),
    ),
)

mail = Mail(app)


# ------------------------------------------------------------------
# Inject site settings (email/phone/socials) into every template
# ------------------------------------------------------------------
@app.context_processor
def inject_settings():
    return {"settings": db.get_settings(), "current_year": datetime.now().year}


# ------------------------------------------------------------------
# Frontend Routes
# ------------------------------------------------------------------
@app.route('/')
def home():
    return render_template('home.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/services')
def services():
    return render_template('services.html')


@app.route('/portfolio')
def portfolio():
    return render_template('portfolio.html', projects=db.list_projects())


@app.route('/thank-you', methods=['GET', 'POST'])
@app.route('/thank-you/', methods=['GET', 'POST'])
def thank_you():
    return render_template('thank-you.html')


# ------------------------------------------------------------------
# Dynamic Project Detail
# ------------------------------------------------------------------
@app.route('/project/<slug>')
def project_detail(slug):
    project = db.get_project(slug)
    if not project:
        abort(404)
    return render_template('project_detail.html', project=project)


# Legacy URLs → redirect to the seeded dynamic slugs (keeps old links alive)
@app.route('/seo_helper_master')
def project1():
    return redirect(url_for('project_detail', slug='seo-master'))


@app.route('/time_center')
def project2():
    return redirect(url_for('project_detail', slug='time-center-ecommerce'))


# ------------------------------------------------------------------
# Contact Form Handler (POST)
# ------------------------------------------------------------------
@app.route('/send_message', methods=['POST'])
def send_message():
    name = request.form.get('name')
    email = request.form.get('email')
    company = request.form.get('company', 'N/A')
    service = request.form.get('service')
    details = request.form.get('details')

    if not name or not email or not service or not details:
        flash("Please fill out all required fields before submitting.", "warning")
        return redirect(url_for('contact'))

    msg_body = f"""
    New message received from your portfolio site:

    Name: {name}
    Email: {email}
    Company: {company}
    Service: {service}

    Message:
    {details}
    """

    try:
        recipient = db.get_settings().get("email")
        msg = Message(subject="New Portfolio Contact Message", recipients=[recipient])
        msg.body = msg_body
        mail.send(msg)
        flash("Thank you for reaching out! Your message has been sent successfully.", "success")
        return redirect(url_for('contact'))
    except Exception as e:
        print("Error sending email:", e)
        flash("Something went wrong while sending your message. Please try again later.", "danger")
        return redirect(url_for('contact'))


# ==================================================================
# ADMIN PORTAL
# ==================================================================
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if auth.is_logged_in():
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if auth.verify_credentials(username, password):
            auth.login_user()
            return redirect(url_for('admin_dashboard'))
        flash("Invalid username or password.", "danger")
    return render_template('admin/login.html')


@app.route('/admin/logout')
def admin_logout():
    auth.logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for('admin_login'))


@app.route('/admin')
@auth.login_required
def admin_dashboard():
    return render_template(
        'admin/dashboard.html',
        projects=db.list_projects(),
        db_ready=db.is_configured(),
        db_error=db.config_error(),
    )


@app.route('/admin/settings', methods=['GET', 'POST'])
@auth.login_required
def admin_settings():
    if request.method == 'POST':
        try:
            db.update_settings({
                "email": request.form.get("email"),
                "phone": request.form.get("phone"),
                "linkedin_url": request.form.get("linkedin_url"),
                "github_url": request.form.get("github_url"),
            })
            flash("Contact details updated.", "success")
            return redirect(url_for('admin_settings'))
        except Exception as e:
            flash(f"Could not save settings: {e}", "danger")
    return render_template('admin/settings.html', settings=db.get_settings())


@app.route('/admin/projects')
@auth.login_required
def admin_projects():
    return render_template('admin/projects_list.html', projects=db.list_projects())


@app.route('/admin/projects/new', methods=['GET', 'POST'])
@auth.login_required
def admin_project_new():
    if request.method == 'POST':
        return _save_project(None)
    return render_template('admin/project_form.html', project=None, action="new")


@app.route('/admin/projects/<project_id>/edit', methods=['GET', 'POST'])
@auth.login_required
def admin_project_edit(project_id):
    project = db.get_project_by_id(project_id)
    if not project:
        abort(404)
    if request.method == 'POST':
        return _save_project(project_id)
    return render_template('admin/project_form.html', project=project, action="edit")


@app.route('/admin/projects/<project_id>/delete', methods=['POST'])
@auth.login_required
def admin_project_delete(project_id):
    try:
        db.delete_project(project_id)
        flash("Project deleted.", "success")
    except Exception as e:
        flash(f"Could not delete project: {e}", "danger")
    return redirect(url_for('admin_projects'))


def _save_project(project_id):
    """Shared create/update handler for the project form."""
    data = {
        "title": request.form.get("title"),
        "short_description": request.form.get("short_description"),
        "overview": request.form.get("overview"),
        "tags": request.form.get("tags"),
        "order": request.form.get("order") or 0,
    }
    if not data["title"]:
        flash("Title is required.", "warning")
        return redirect(request.url)

    try:
        card_url = db.upload_image(request.files.get("card_image"))
        if card_url:
            data["card_image_url"] = card_url

        # ---- Gallery images (feed the detail-page slider) ----
        # Start from whatever the project already has (edit), drop the ones the
        # user marked for removal, then append any newly uploaded files.
        gallery = []
        if project_id:
            existing = db.get_project_by_id(project_id) or {}
            gallery = list(existing.get("gallery_urls") or [])
            # Back-compat: seed the gallery from a legacy single preview image
            # so editing an old project doesn't lose it.
            if not gallery and existing.get("preview_image_url"):
                gallery = [existing["preview_image_url"]]
            to_remove = set(request.form.getlist("remove_gallery"))
            gallery = [u for u in gallery if u not in to_remove]

        gallery.extend(db.upload_images(request.files.getlist("gallery_images")))
        data["gallery_urls"] = gallery

        # Keep the first gallery image as the preview (legacy field / fallback),
        # and use it as the card thumbnail on create when none was uploaded.
        if gallery:
            data["preview_image_url"] = gallery[0]
            if not card_url and not project_id:
                data["card_image_url"] = gallery[0]

        if project_id:
            db.update_project(project_id, data)
            flash("Project updated.", "success")
        else:
            db.create_project(data)
            flash("Project created.", "success")

        if db.gallery_column_missing():
            flash(
                "Gallery images were not saved: your database is missing the "
                "'gallery_urls' column. Run this once in the Supabase SQL editor, "
                "then re-save: "
                "ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS gallery_urls text[] DEFAULT '{}';",
                "warning",
            )
        return redirect(url_for('admin_projects'))
    except Exception as e:
        flash(f"Could not save project: {e}", "danger")
        return redirect(request.url)


@app.route('/admin/seed', methods=['POST'])
@auth.login_required
def admin_seed():
    """One-time: insert the two original projects if the list is empty."""
    if db.list_projects():
        flash("Projects already exist — seeding skipped.", "warning")
        return redirect(url_for('admin_projects'))

    seed = [
        {
            "title": "SEO Master",
            "slug": "seo-master",
            "short_description": "SEO Master Dashboard, a modern Flask-based web application designed to help users manage and optimize their SEO performance.",
            "overview": "Welcome to the SEO Master Dashboard, a modern Flask-based web application designed to help users manage and optimize their SEO performance. This project features a sleek, user-friendly interface with a homepage, feature pages (About, Services, Contact), and a secure dashboard with multiple tools for SEO analysis. User authentication (login/signup) is implemented with data stored in a PostgreSQL database.",
            "tags": ["Selenium", "Postman", "Jenkins", "JMeter"],
            "card_image_url": "/static/images/project1.png",
            "preview_image_url": "/static/images/project1.png",
            "order": 1,
        },
        {
            "title": "Time Center E-Commerce",
            "slug": "time-center-ecommerce",
            "short_description": "Time Center is a modern and fully responsive eCommerce platform for luxury watches, designed with elegant UI and optimized for fast performance.",
            "overview": "Time Center is a modern, web-based eCommerce platform developed using Next.js and hosted on Vercel, designed for purchasing premium watches with a seamless and elegant shopping experience. The platform allows users to browse products, view detailed descriptions, manage their cart, and complete secure checkouts through a fast and responsive interface.",
            "tags": ["Selenium", "Postman", "Jenkins", "JMeter"],
            "card_image_url": "/static/images/project2.png",
            "preview_image_url": "/static/images/project2.png",
            "order": 2,
        },
    ]
    try:
        for p in seed:
            db.create_project(p)
        flash("Seeded 2 starter projects.", "success")
    except Exception as e:
        flash(f"Seeding failed: {e}", "danger")
    return redirect(url_for('admin_projects'))


# ------------------------------------------------------------------
# Run Flask App
# ------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
