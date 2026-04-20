import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Market Research Dashboard",
  description: "Institutional investment research intelligence",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-gray-950 text-gray-100 min-h-screen">
        <header className="border-b border-gray-800 px-6 py-4">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <h1 className="text-xl font-bold tracking-tight">
              Market Research Intelligence
            </h1>
            <span className="text-sm text-gray-500">
              Institutional Research Scraper
            </span>
          </div>
        </header>
        <main className="max-w-7xl mx-auto px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
