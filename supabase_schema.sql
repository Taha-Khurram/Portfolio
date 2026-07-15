-- ============================================================
-- Supabase schema for the SQA portfolio.
-- Run this in the Supabase dashboard → SQL Editor.
-- ============================================================

-- ---- Site settings (single row, keyed 'site') ----
create table if not exists public.settings (
    id           text primary key,
    email        text,
    phone        text,
    linkedin_url text,
    github_url   text
);

-- ---- Projects ----
create table if not exists public.projects (
    id                uuid primary key default gen_random_uuid(),
    title             text not null,
    slug              text unique,
    short_description text,
    overview          text,
    tags              text[] default '{}',
    card_image_url    text,
    preview_image_url text,
    gallery_urls      text[] default '{}',
    sort_order        integer default 0,
    created_at        timestamptz default now()
);

-- For databases created before the gallery feature: add the column if missing.
alter table public.projects add column if not exists gallery_urls text[] default '{}';

create index if not exists projects_sort_order_idx on public.projects (sort_order, created_at);

-- ---- Testimonials ("What Clients Say" cards on the home page) ----
create table if not exists public.testimonials (
    id          uuid primary key default gen_random_uuid(),
    quote       text not null,
    name        text,
    role        text,
    sort_order  integer default 0,
    created_at  timestamptz default now()
);

create index if not exists testimonials_sort_order_idx on public.testimonials (sort_order, created_at);

-- ---- Professional experience (About page timeline, LinkedIn-style) ----
create table if not exists public.experiences (
    id             uuid primary key default gen_random_uuid(),
    title          text not null,          -- role, e.g. "QA Automation Engineer"
    company        text,                   -- "Genius Mind Zone — Faisalabad, Pakistan"
    period         text,                   -- "May 2026 - Present · 3 mos"
    bullets        text[] default '{}',    -- responsibility lines
    reference_url  text,                   -- LinkedIn reference link
    sort_order     integer default 0,
    created_at     timestamptz default now()
);

create index if not exists experiences_sort_order_idx on public.experiences (sort_order, created_at);

-- ============================================================
-- Storage bucket for uploaded project images.
-- The app uses the SERVICE ROLE key, which bypasses RLS, so no
-- extra storage policies are required for admin uploads. The
-- bucket is public so the uploaded image URLs are readable by
-- anyone visiting the site.
-- ============================================================
insert into storage.buckets (id, name, public)
values ('project-images', 'project-images', true)
on conflict (id) do update set public = excluded.public;

-- ============================================================
-- Row Level Security
-- The app connects with the SERVICE ROLE key (server-side only),
-- which bypasses RLS entirely — so enabling RLS below keeps the
-- tables locked down to anonymous/public clients while the app
-- keeps full access. If you ever switch the app to the ANON key,
-- add explicit policies for the reads/writes you want to allow.
-- ============================================================
alter table public.settings enable row level security;
alter table public.projects enable row level security;
alter table public.testimonials enable row level security;
alter table public.experiences enable row level security;
