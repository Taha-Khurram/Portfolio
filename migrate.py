"""
One-off database migrations for the portfolio.

Adds any columns the app needs that may be missing from an older database.
Currently: projects.gallery_urls (multi-image support).

Usage:
  1. Get your database connection string from Supabase:
       Dashboard -> Project Settings -> Database -> Connection string -> URI
     It looks like:
       postgresql://postgres:YOUR-PASSWORD@db.<ref>.supabase.co:5432/postgres
  2. Put it in .env as SUPABASE_DB_URL (or DATABASE_URL), then run:
       python migrate.py

The password is NEVER sent anywhere except directly to your database.
"""

import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

MIGRATIONS = [
    # (description, SQL)
    (
        "projects.gallery_urls (multi-image gallery)",
        "alter table public.projects "
        "add column if not exists gallery_urls text[] default '{}';",
    ),
    (
        "testimonials table (What Clients Say cards)",
        "create table if not exists public.testimonials ("
        "  id uuid primary key default gen_random_uuid(),"
        "  quote text not null,"
        "  name text,"
        "  role text,"
        "  sort_order integer default 0,"
        "  created_at timestamptz default now()"
        ");"
        "create index if not exists testimonials_sort_order_idx "
        "  on public.testimonials (sort_order, created_at);"
        "alter table public.testimonials enable row level security;",
    ),
    (
        "experiences table (About-page professional timeline)",
        "create table if not exists public.experiences ("
        "  id uuid primary key default gen_random_uuid(),"
        "  title text not null,"
        "  company text,"
        "  period text,"
        "  bullets text[] default '{}',"
        "  reference_url text,"
        "  sort_order integer default 0,"
        "  created_at timestamptz default now()"
        ");"
        "create index if not exists experiences_sort_order_idx "
        "  on public.experiences (sort_order, created_at);"
        "alter table public.experiences enable row level security;",
    ),
]


def main():
    db_url = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        print(
            "ERROR: set SUPABASE_DB_URL (or DATABASE_URL) in .env first.\n"
            "Find it in Supabase -> Project Settings -> Database -> "
            "Connection string -> URI."
        )
        sys.exit(1)

    try:
        import psycopg2
    except ImportError:
        print(
            "ERROR: psycopg2 is not installed. Run:\n"
            "  pip install psycopg2-binary"
        )
        sys.exit(1)

    print("Connecting to the database...")
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            for desc, sql in MIGRATIONS:
                print(f"  -> {desc}")
                cur.execute(sql)
            # Ask PostgREST (Supabase's API layer) to reload its schema cache
            # so the new column is usable immediately, not after a delay.
            cur.execute("notify pgrst, 'reload schema';")
        print("Migrations applied successfully.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
