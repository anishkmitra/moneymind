"use client";

import { useEffect, useState } from "react";
import { supabase, type Article } from "@/lib/supabase";
import ReactMarkdown from "react-markdown";

const FIRM_COLORS: Record<string, string> = {
  "citadel-securities": "bg-blue-900/50 text-blue-300",
  bridgewater: "bg-emerald-900/50 text-emerald-300",
  blackrock: "bg-purple-900/50 text-purple-300",
  aqr: "bg-orange-900/50 text-orange-300",
  "two-sigma": "bg-pink-900/50 text-pink-300",
  "man-group": "bg-cyan-900/50 text-cyan-300",
  "de-shaw": "bg-yellow-900/50 text-yellow-300",
  "jpmorgan-am": "bg-indigo-900/50 text-indigo-300",
  "goldman-sachs-am": "bg-amber-900/50 text-amber-300",
};

export default function Home() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedFirm, setSelectedFirm] = useState<string>("all");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    fetchArticles();
  }, []);

  async function fetchArticles() {
    const { data, error } = await supabase
      .from("articles")
      .select("*")
      .order("scraped_at", { ascending: false })
      .limit(100);

    if (error) {
      console.error("Failed to fetch articles:", error);
    } else {
      setArticles(data || []);
    }
    setLoading(false);
  }

  const firms = [...new Set(articles.map((a) => a.firm_slug))].sort();
  const filtered =
    selectedFirm === "all"
      ? articles
      : articles.filter((a) => a.firm_slug === selectedFirm);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500 text-lg">Loading research...</div>
      </div>
    );
  }

  return (
    <div>
      {/* Stats bar */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <div className="text-3xl font-bold">{articles.length}</div>
          <div className="text-sm text-gray-500">Total Articles</div>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <div className="text-3xl font-bold">{firms.length}</div>
          <div className="text-sm text-gray-500">Firms Tracked</div>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <div className="text-3xl font-bold">
            {articles.filter((a) => a.pdf_storage_paths?.length > 0).length}
          </div>
          <div className="text-sm text-gray-500">PDFs Stored</div>
        </div>
      </div>

      {/* Filter */}
      <div className="flex gap-2 mb-6 flex-wrap">
        <button
          onClick={() => setSelectedFirm("all")}
          className={`px-3 py-1 rounded-full text-sm transition-colors ${
            selectedFirm === "all"
              ? "bg-white text-black"
              : "bg-gray-800 text-gray-400 hover:bg-gray-700"
          }`}
        >
          All
        </button>
        {firms.map((slug) => (
          <button
            key={slug}
            onClick={() => setSelectedFirm(slug)}
            className={`px-3 py-1 rounded-full text-sm transition-colors ${
              selectedFirm === slug
                ? "bg-white text-black"
                : `${FIRM_COLORS[slug] || "bg-gray-800 text-gray-400"} hover:opacity-80`
            }`}
          >
            {slug}
          </button>
        ))}
      </div>

      {/* Articles list */}
      {filtered.length === 0 ? (
        <div className="text-center py-16 text-gray-600">
          <p className="text-lg">No articles yet.</p>
          <p className="text-sm mt-2">
            Run <code className="bg-gray-800 px-2 py-0.5 rounded">scraper scrape</code> to fetch research.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filtered.map((article) => (
            <div
              key={article.id}
              className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden"
            >
              <button
                onClick={() =>
                  setExpandedId(expandedId === article.id ? null : article.id)
                }
                className="w-full text-left p-5 hover:bg-gray-800/50 transition-colors"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-medium ${
                          FIRM_COLORS[article.firm_slug] ||
                          "bg-gray-800 text-gray-400"
                        }`}
                      >
                        {article.firm_slug}
                      </span>
                      {article.pdf_storage_paths?.length > 0 && (
                        <span className="text-xs text-red-400">PDF</span>
                      )}
                    </div>
                    <h2 className="font-semibold text-lg leading-tight">
                      {article.title}
                    </h2>
                  </div>
                  <div className="text-sm text-gray-500 whitespace-nowrap">
                    {(article.published_date || article.scraped_at || "").slice(
                      0,
                      10
                    )}
                  </div>
                </div>
              </button>

              {expandedId === article.id && (
                <div className="border-t border-gray-800 p-5">
                  {article.summary ? (
                    <div className="prose prose-invert prose-sm max-w-none">
                      <ReactMarkdown>{article.summary}</ReactMarkdown>
                    </div>
                  ) : (
                    <p className="text-gray-500 italic">No summary available.</p>
                  )}
                  <div className="mt-4 flex gap-3">
                    <a
                      href={article.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-blue-400 hover:text-blue-300"
                    >
                      View original
                    </a>
                    {article.pdf_urls?.map((url, i) => (
                      <a
                        key={i}
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-red-400 hover:text-red-300"
                      >
                        PDF {i + 1}
                      </a>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
