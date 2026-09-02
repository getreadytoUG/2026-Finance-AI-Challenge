// 인디고 브리핑: 고정 좌측 내비게이션과 넓은 브리핑 캔버스로 로그인 후 경험을 랜딩과 연결한다.
// (레퍼런스의 DashboardLayout에서 사이드바+topbar 셸만 분리 — Next.js에서는 이 부분을
// 진짜 layout.tsx로 한 번만 마운트해야 탭 이동마다 사이드바가 깜빡이거나 폴링이
// 재시작되지 않는다. 페이지별 eyebrow/title/action 헤더는 DashboardLayout.tsx가 맡는다.)
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  BarChart3,
  Bell,
  ClipboardList,
  FolderOpen,
  Heart,
  Home,
  LogOut,
  PiggyBank,
  Search,
  Settings,
  Users,
  X,
} from "lucide-react";
import { BrandMark } from "./BrandMark";
import { SiteHeader } from "./SiteHeader";
import ChatWidget from "./ChatWidget";
import { getMe, getRecommendations, isTokenExpired } from "@/lib/api";

// 2026-09-01 UPGRADE.md 반영: "AI 분석 리포트"는 독립 탭이 아니라 "정책 달력" 안의
// "AI 정책 검색" 기능으로 흡수됐다(RecommendationCalendar 옆 세 번째 서브탭 참고) —
// 그래서 여기 더 이상 /ai-search 항목이 없다. "저축플랜"은 정책연계형 저축/주거
// 시뮬레이터로 내용이 바뀌었을 뿐 탭 자체는 되살아났다. "정책 매칭"이라는 상위
// 탭도 폐기되고, 그 아래 있던 두 기능이 각자 독립 탭으로 분리됐다(같은 날 사용자
// 재지시) — "내 맞춤 정책 보기"(/policy)와 "혼인신고 계산기"(/marriage).
const NAV_ITEMS = [
  { href: "/dashboard", label: "한눈에 보기", icon: Home },
  { href: "/policy", label: "내 맞춤 정책 보기", icon: Search },
  { href: "/marriage", label: "혼인신고 계산기", icon: Heart },
  { href: "/savings", label: "저축플랜", icon: PiggyBank },
  { href: "/recommendations", label: "정책 달력", icon: Bell },
];

const ADMIN_NAV_ITEMS = [
  { href: "/admin", label: "개요", icon: BarChart3 },
  { href: "/admin/users", label: "회원", icon: Users },
  { href: "/admin/policies", label: "정책", icon: FolderOpen },
  { href: "/admin/policies/list", label: "정책 목록", icon: ClipboardList },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [userLabel, setUserLabel] = useState("");
  const [unreadCount, setUnreadCount] = useState(0);
  const [open, setOpen] = useState(false);
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
    // the effect without breaking SSR — one-time auth gate.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setReady(true);
  }, [router]);

  useEffect(() => {
    if (!ready) return;
    const token = localStorage.getItem("token") ?? "";
    getMe(token)
      .then((profile) => {
        // 소셜 로그인 유저는 프로필을 채우기 전까지 앱 탭에 접근할 수 없다.
        if (!profile.is_admin && !profile.profile_complete) {
          router.replace("/onboarding");
          return;
        }
        setIsAdmin(profile.is_admin);
        setUserLabel(profile.name || profile.email);
      })
      .catch(() => {});
  }, [ready, router]);

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
    const toggle = () => setOpen((value) => !value);
    window.addEventListener("toggle-sidebar", toggle);
    return () => window.removeEventListener("toggle-sidebar", toggle);
  }, []);

  function handleLogout() {
    localStorage.removeItem("token");
    router.push("/login");
  }

  if (!ready) return null;

  const navItems = isAdmin ? ADMIN_NAV_ITEMS : NAV_ITEMS;
  // 사이드바 상단 브랜드마크는 "대시보드로 돌아가기"가 아니라 "홈페이지로 나가기"다
  // (사용자 요청, 2026-09-02) — 대시보드로 들어가는 진입점은 이제 상단 "한눈에 보기"
  // 탭과 공개 헤더의 "대시보드" 링크가 맡는다. 관리자는 별도 공개 랜딩이 없으므로
  // 그대로 /admin 유지.
  const homeHref = isAdmin ? "/admin" : "/";
  // 정책 달력 페이지엔 이미 챗봇이 내장돼 있다(캘린더 탭의 범용 챗봇 + AI 정책
  // 검색 탭의 정책별 챗봇) — 떠다니는 ChatWidget까지 겹치면 중복이라 숨긴다.
  const showChatWidget = !isAdmin && pathname !== "/recommendations";

  return (
    <div className="app-shell min-h-screen bg-[#f7f9fc] text-ink">
      <aside
        className={`app-sidebar fixed inset-y-0 left-0 z-40 flex w-[248px] flex-col border-r border-[#e5ebf5] bg-white px-5 py-6 transition-transform duration-200 lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}
      >
        <div className="mb-10 flex items-center justify-between px-2">
          <Link href={homeHref} onClick={() => setOpen(false)}>
            <BrandMark size="sm" />
          </Link>
          <button className="rounded-lg p-1 text-slate-400 lg:hidden" onClick={() => setOpen(false)} aria-label="사이드바 닫기">
            <X size={18} />
          </button>
        </div>
        <div className="mb-3 px-3 text-[10px] font-extrabold uppercase tracking-[0.18em] text-slate-400">
          {isAdmin ? "Admin" : "My briefing"}
        </div>
        <nav className="grid gap-1" aria-label="서비스 내비게이션">
          {navItems.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            const count = href === "/recommendations" && unreadCount > 0 ? String(unreadCount) : undefined;
            return (
              <Link
                key={href}
                href={href}
                onClick={() => setOpen(false)}
                className={`group flex items-center justify-between rounded-xl px-3 py-3 text-[13px] font-bold transition ${active ? "bg-[#eef3ff] text-[#2457d6]" : "text-slate-500 hover:bg-slate-50 hover:text-ink"}`}
              >
                <span className="flex items-center gap-3">
                  <Icon size={17} strokeWidth={active ? 2.2 : 1.8} />
                  <span>{label}</span>
                </span>
                {count && (
                  <span className={`rounded-full px-2 py-0.5 text-[10px] ${active ? "bg-[#2457d6] text-white" : "bg-slate-100 text-slate-400"}`}>
                    {count}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
        {!isAdmin && (
          <>
            <div className="my-7 h-px bg-slate-100" />
            <div className="mb-3 px-3 text-[10px] font-extrabold uppercase tracking-[0.18em] text-slate-400">Support</div>
            <nav className="grid gap-1">
              <Link
                href="/profile"
                className="flex items-center gap-3 rounded-xl px-3 py-3 text-left text-[13px] font-bold text-slate-500 transition hover:bg-slate-50 hover:text-ink"
              >
                <Settings size={17} strokeWidth={1.8} />
                프로필 설정
              </Link>
            </nav>
          </>
        )}
        <div className="mt-auto">
          <button className="flex items-center gap-3 px-3 text-[12px] font-bold text-slate-400 hover:text-slate-600" onClick={handleLogout}>
            <LogOut size={16} strokeWidth={1.8} />
            로그아웃
          </button>
        </div>
      </aside>
      {open && <button className="fixed inset-0 z-30 bg-ink/20 lg:hidden" onClick={() => setOpen(false)} aria-label="메뉴 닫기" />}
      <div className="lg:pl-[248px]">
        <SiteHeader app userLabel={userLabel} unreadCount={unreadCount} />
        <main className="mx-auto max-w-[1440px] px-4 pb-16 pt-8 sm:px-8 lg:px-12 lg:pt-10">{children}</main>
      </div>
      {showChatWidget && <ChatWidget />}
    </div>
  );
}
