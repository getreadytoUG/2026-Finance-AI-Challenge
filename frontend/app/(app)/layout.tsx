"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  FaBell,
  FaBookOpen,
  FaChartLine,
  FaClipboardList,
  FaFolderOpen,
  FaLandmark,
  FaPiggyBank,
  FaRightFromBracket,
  FaSeedling,
  FaUser,
  FaUsers,
  FaWandMagicSparkles,
} from "react-icons/fa6";
import type { IconType } from "react-icons";
import { getMe, getRecommendations, isTokenExpired } from "@/lib/api";
import ChatWidget from "@/components/ChatWidget";

const TABS: { href: string; label: string; icon: IconType }[] = [
  { href: "/policy", label: "금융 정책 추천", icon: FaLandmark },
  { href: "/browse", label: "정책 읽기", icon: FaBookOpen },
  { href: "/ai-search", label: "AI로 정책 알기", icon: FaWandMagicSparkles },
  { href: "/savings", label: "저축플랜", icon: FaPiggyBank },
  { href: "/recommendations", label: "추천", icon: FaBell },
];

// 관리자 계정은 일반 사용자용 탭이 필요 없다 — 대시보드 전용 탭만 보여준다.
const ADMIN_TABS: { href: string; label: string; icon: IconType }[] = [
  { href: "/admin", label: "개요", icon: FaChartLine },
  { href: "/admin/users", label: "회원", icon: FaUsers },
  { href: "/admin/policies", label: "정책", icon: FaFolderOpen },
  { href: "/admin/policies/list", label: "정책 목록", icon: FaClipboardList },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isAdmin, setIsAdmin] = useState(false);
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token || isTokenExpired(token)) {
      localStorage.removeItem("token");
      router.push("/login");
      return;
    }
    // localStorage only exists client-side, so this check can't move out of
    // the effect without breaking SSR — the resulting render (browser has a
    // token, so show the page) isn't cascading, it's the intended one-time gate.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setReady(true);
  }, [router]);

  useEffect(() => {
    if (!ready) return;
    const token = localStorage.getItem("token") ?? "";
    function poll() {
      getRecommendations(token)
        .then((res) => setUnreadCount(res.unread_count))
        .catch(() => {});
    }
    poll();
    const interval = setInterval(poll, 60000);
    return () => clearInterval(interval);
  }, [ready]);

  useEffect(() => {
    if (!ready) return;
    const token = localStorage.getItem("token") ?? "";
    getMe(token)
      .then((profile) => setIsAdmin(profile.is_admin))
      .catch(() => {});
  }, [ready]);

  const tabs = isAdmin ? ADMIN_TABS : TABS;

  function handleLogout() {
    localStorage.removeItem("token");
    router.push("/login");
  }

  if (!ready) return null;

  return (
    <div style={{ minHeight: "100vh" }}>
      <header className="app-header">
        <div className="app-header-inner">
          <Link href={isAdmin ? "/admin" : "/policy"} className="app-logo">
            <span className="icon-box icon-box-solid icon-box-sm">
              <FaSeedling />
            </span>
            청년/신혼부부 금융 도우미
          </Link>
          <nav className="app-nav">
            {tabs.map((tab) => {
              const active = pathname === tab.href;
              const Icon = tab.icon;
              return (
                <Link key={tab.href} href={tab.href} className={`app-nav-tab${active ? " active" : ""}`}>
                  <Icon />
                  {tab.label}
                  {tab.href === "/recommendations" && unreadCount > 0 && (
                    <span className="app-nav-badge">{unreadCount}</span>
                  )}
                </Link>
              );
            })}
          </nav>
          <div className="app-header-actions">
            <Link
              href="/profile"
              className="btn-ghost"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                color: pathname === "/profile" ? "var(--primary)" : undefined,
              }}
            >
              <FaUser />
              내 정보
            </Link>
            <button
              className="btn-ghost"
              style={{ display: "inline-flex", alignItems: "center", gap: 6 }}
              onClick={handleLogout}
            >
              <FaRightFromBracket />
              로그아웃
            </button>
          </div>
        </div>
      </header>
      <div className={pathname === "/ai-search" ? "page page-wide" : "page"} style={{ paddingTop: 32 }}>
        {children}
      </div>
      {pathname !== "/ai-search" && !pathname.startsWith("/admin") && <ChatWidget />}
    </div>
  );
}
