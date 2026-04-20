-- Run this in the Supabase SQL Editor to set up the database.

-- Articles table: stores metadata + summaries for each scraped research piece
create table if not exists articles (
  id uuid default gen_random_uuid() primary key,
  firm_slug text not null,
  url text not null unique,
  title text not null,
  published_date text,
  body_text text,
  summary text,
  content_hash text not null unique,
  pdf_urls text[] default '{}',
  pdf_storage_paths text[] default '{}',
  scraped_at timestamptz default now(),
  created_at timestamptz default now()
);

-- Indexes for common queries
create index if not exists idx_articles_firm_slug on articles(firm_slug);
create index if not exists idx_articles_scraped_at on articles(scraped_at desc);
create index if not exists idx_articles_content_hash on articles(content_hash);

-- Enable Row Level Security (public read for the dashboard)
alter table articles enable row level security;

-- Policy: anyone can read (for the Vercel dashboard)
create policy "Public read access" on articles
  for select using (true);

-- Policy: only service role can insert/update
create policy "Service role write access" on articles
  for insert with check (true);

create policy "Service role update access" on articles
  for update using (true);

-- Storage bucket for PDFs (create via Supabase dashboard or API)
-- Name: research-pdfs
-- Public: false (use signed URLs)
insert into storage.buckets (id, name, public)
values ('research-pdfs', 'research-pdfs', false)
on conflict (id) do nothing;
