"use client";

import Link from "next/link";
import type { Route } from "next";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo } from "react";

import { useAuth } from "./auth-provider";

const navItems: Array<{ href: Route; label: string }> = [
  { href: "/", label: "Dashboard" },
  { href: "/jobs/new", label: "New Job" },
  { href: "/price-checker", label: "Price Checker" },
  { href: "/knowledge-review", label: "Knowledge Review" },
];


export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { configured, loading, user, signOutUser } = useAuth();

  const isLoginPage = pathname === "/login";
  const authRequired = configured && !isLoginPage;
  const isAllowed = !configured || Boolean(user) || isLoginPage;

  useEffect(() => {
    if (!authRequired || loading || user) {
      return;
    }
    router.replace("/login");
  }, [authRequired, loading, router, user]);

  const authSummary = useMemo(() => {
    if (!configured) {
      return "Auth not configured";
    }
    if (loading) {
      return "Checking session...";
    }
    if (user?.email) {
      return user.email;
    }
    return "Signed out";
  }, [configured, loading, user]);

  if (authRequired && !isAllowed) {
    return (
      <div className="centeredPanel">
        <div className="card">
          <span className="pill">Secure Workspace</span>
          <h3>Checking your session</h3>
          <p className="helperText">The BOQ AUTO workspace is waiting for Firebase Auth to confirm your sign-in.</p>
        </div>
      </div>
    );
  }

  return (
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
        <div className="authPanel">
          <span className="pill">Access</span>
          <p className="helperText">{authSummary}</p>
          {configured && user ? (
            <button type="button" className="secondaryButton" onClick={() => void signOutUser()}>
              Sign Out
            </button>
          ) : null}
        </div>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}
