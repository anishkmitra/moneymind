import { createClient } from "@supabase/supabase-js";

export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

export type Article = {
  id: string;
  firm_slug: string;
  url: string;
  title: string;
  published_date: string | null;
  summary: string | null;
  content_hash: string;
  pdf_urls: string[];
  pdf_storage_paths: string[];
  scraped_at: string;
};
