"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

const TABS = [
  { href: "/policy", label: "정책비교", icon: "🏛️" },
  { href: "/savings", label: "저축플랜", icon: "💰" },
  { href: "/subscriptions", label: "구독료 리포트", icon: "📺" },
  { href: "/cards", label: "카드소비 리포트", icon: "💳" },
  { href: "/recommendations", label: "추천", icon: "🔔" },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (!localStorage.getItem("token")) {
      router.push("/login");
      return;
    }
    // localStorage only exists client-side, so this check can't move out of
    // the effect without breaking SSR — the resulting render (browser has a
    // token, so show the page) isn't cascading, it's the intended one-time gate.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setReady(true);
  }, [router]);

  function handleLogout() {
    localStorage.removeItem("token");
    router.push("/login");
  }

  if (!ready) return null;

  return (
    <div style={{ minHeight: "100vh" }}>
      <header
        style={{
          position: "sticky",
          top: 0,
          zIndex: 10,
          background: "var(--surface)",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <div
          className="nav-bar"
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "16px 20px",
            marginBottom: 0,
          }}
        >
          <span style={{ fontSize: 20, marginRight: 8 }}>🌱</span>
          <nav style={{ display: "flex", gap: 4, flex: 1, flexWrap: "nowrap", overflowX: "auto" }}>
            {TABS.map((tab) => {
              const active = pathname === tab.href;
              return (
                <Link
                  key={tab.href}
                  href={tab.href}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    padding: "8px 14px",
                    borderRadius: 999,
                    fontSize: 14,
                    fontWeight: 600,
                    color: active ? "var(--primary)" : "var(--text-muted)",
                    background: active ? "var(--primary-tint)" : "transparent",
                  }}
                >
                  <span>{tab.icon}</span>
                  {tab.label}
                </Link>
              );
            })}
          </nav>
          <button className="btn btn-ghost" onClick={handleLogout}>
            로그아웃
          </button>
        </div>
      </header>
      <div className="page" style={{ paddingTop: 32 }}>
        {children}
      </div>
    </div>
  );
}
