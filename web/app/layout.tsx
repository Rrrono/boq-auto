import "./globals.css";
import Link from "next/link";
import type { ReactNode } from "react";

export const metadata = {
  title: "BOQ AUTO Web",
  description: "Kenyan construction estimating and price intelligence platform.",
};

const navItems = [
  { href: "/", label: "Dashboard" },
  { href: "/jobs/new", label: "New Job" },
  { href: "/price-checker", label: "Price Checker" },
  { href: "/knowledge-review", label: "Knowledge Review" },
];

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <aside className="sidebar">
            <h1 className="brand">BOQ AUTO</h1>
            <p className="tagline">
              Kenyan BOQ automation, tender extraction, and regional price intelligence in one workspace.
            </p>
            <nav className="nav">
              {navItems.map((item) => (
                <Link key={item.href} href={item.href}>
                  {item.label}
                </Link>
              ))}
            </nav>
          </aside>
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}
