"""
Static Site Generator for Netlify Deployment
Converts Flask/Jinja2 templates to static HTML files
"""

import os
import shutil
from jinja2 import Environment, FileSystemLoader

# Configuration
TEMPLATE_DIR = "templates"
STATIC_DIR = "static"
OUTPUT_DIR = "dist"

# Pages to generate: (template_name, output_path, page_endpoint)
PAGES = [
    ("home.html", "index.html", "home"),
    ("about.html", "about/index.html", "about"),
    ("contact.html", "contact/index.html", "contact"),
    ("services.html", "services/index.html", "services"),
    ("portfolio.html", "portfolio/index.html", "portfolio"),
    ("seo_helper_master.html", "seo_helper_master/index.html", "project1"),
    ("time_center_ecommerce.html", "time_center/index.html", "project2"),
]


def url_for(endpoint, **kwargs):
    """Mock Flask's url_for function for static site generation"""
    if endpoint == "static":
        filename = kwargs.get("filename", "")
        return f"/static/{filename}"

    # Map endpoints to URLs
    url_map = {
        "home": "/",
        "about": "/about",
        "contact": "/contact",
        "services": "/services",
        "portfolio": "/portfolio",
        "project1": "/seo_helper_master",
        "project2": "/time_center",
    }
    return url_map.get(endpoint, "/")


class MockRequest:
    """Mock Flask's request object"""
    def __init__(self, endpoint):
        self.endpoint = endpoint


def build_site():
    """Build the static site"""

    # Clean and create output directory
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    # Copy static files
    static_dest = os.path.join(OUTPUT_DIR, "static")
    shutil.copytree(STATIC_DIR, static_dest)
    print(f"Copied static files to {static_dest}")

    # Set up Jinja2 environment
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

    # Generate each page
    for template_name, output_path, endpoint in PAGES:
        try:
            template = env.get_template(template_name)

            # Render with mock Flask context
            html = template.render(
                url_for=url_for,
                request=MockRequest(endpoint),
                get_flashed_messages=lambda with_categories=False: []
            )

            # Create output directory if needed
            full_output_path = os.path.join(OUTPUT_DIR, output_path)
            os.makedirs(os.path.dirname(full_output_path), exist_ok=True)

            # Write the HTML file
            with open(full_output_path, "w", encoding="utf-8") as f:
                f.write(html)

            print(f"Generated: {output_path}")

        except Exception as e:
            print(f"Error generating {template_name}: {e}")
            raise

    print(f"\nBuild complete! Output in '{OUTPUT_DIR}' directory")


if __name__ == "__main__":
    build_site()
