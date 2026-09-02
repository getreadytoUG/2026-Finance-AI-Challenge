// 인디고 브리핑: 공개 화면은 탐색형 헤더, 앱 화면은 동일한 mark와 프로필 액션으로 연결한다.
"use client";

import { ArrowRight, Bell, ChevronDown, Menu, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { isTokenExpired } from "@/lib/api";
import { BrandMark } from "./BrandMark";

export function SiteHeader({
  app = false,
  userLabel,
  unreadCount = 0,
}: {
  app?: boolean;
  userLabel?: string;
  unreadCount?: number;
}) {
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  // 공개 헤더(app=false)는 로그인 상태와 무관하게 항상 "로그인"/"내 맞춤 혜택
  // 진단"(회원가입 유도) 버튼을 그대로 보여주고 있었다 — 로그인 후에도 홈페이지가
  // 먼저 보이도록 바뀌면서(2026-09-02) 이게 "로그인이 풀린 것처럼 보인다"는
  // 혼동으로 이어졌다(실제로는 토큰이 그대로 남아있음, 사용자 재확인 필요해서
  // Playwright로 직접 검증함). 그래서 여기서도 로그인 여부를 확인해 버튼을 바꾼다.
  const [loggedIn, setLoggedIn] = useState(false);

  useEffect(() => {
    if (app) return; // app 토프바는 AppShell이 이미 인증 가드를 거친 뒤에만 렌더링되므로 불필요.
    // localStorage only exists client-side, so this check can't move out of
    // the effect without breaking SSR — one-time auth gate(AppShell.tsx와 동일 패턴).
    const token = localStorage.getItem("token");
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoggedIn(!!token && !isTokenExpired(token));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleLogout() {
    localStorage.removeItem("token");
    setLoggedIn(false);
    router.push("/login");
  }

  const initials = (userLabel ?? "").slice(0, 2).toUpperCase() || "ME";

  if (app) {
    return (
      <header className="app-topbar sticky top-0 z-30 border-b border-slate-200/80 bg-[#f7f9fc]/90 backdrop-blur-xl">
        <div className="flex items-center justify-between gap-4 px-4 py-3 sm:px-8 lg:px-10">
          <button
            className="rounded-xl p-2 text-slate-500 hover:bg-white lg:hidden"
            aria-label="메뉴 열기"
            onClick={() => window.dispatchEvent(new CustomEvent("toggle-sidebar"))}
          >
            <Menu size={20} />
          </button>
          <div className="hidden items-center lg:flex">
            <BrandMark size="sm" />
          </div>
          <div className="ml-auto flex items-center gap-3">
            <Link
              href="/recommendations"
              className="relative rounded-xl p-2.5 text-slate-500 transition hover:bg-white hover:text-ink"
              aria-label="추천 알림 보기"
            >
              <Bell size={18} strokeWidth={1.8} />
              {unreadCount > 0 && (
                <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-[#1eb8a6]" />
              )}
            </Link>
            <div className="relative">
              <button
                onClick={() => setProfileOpen(!profileOpen)}
                className="flex items-center gap-2 rounded-xl bg-white py-1.5 pl-1.5 pr-2.5 text-left shadow-sm ring-1 ring-slate-200/80 transition hover:ring-blue-200"
                aria-expanded={profileOpen}
              >
                <span className="grid h-8 w-8 place-items-center rounded-[10px] bg-[#e8f0ff] text-xs font-extrabold text-[#2457d6]">
                  {initials}
                </span>
                <ChevronDown size={14} className="text-slate-400" />
              </button>
              {profileOpen && (
                <div className="absolute right-0 top-12 w-40 rounded-2xl bg-white p-1.5 shadow-[0_16px_40px_rgba(16,35,71,.14)] ring-1 ring-slate-200">
                  <Link
                    href="/profile"
                    onClick={() => setProfileOpen(false)}
                    className="block w-full rounded-xl px-3 py-2.5 text-left text-xs font-bold text-slate-600 hover:bg-slate-50"
                  >
                    내 정보
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="w-full rounded-xl px-3 py-2.5 text-left text-xs font-bold text-slate-600 hover:bg-slate-50"
                  >
                    로그아웃
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>
    );
  }

  return (
    <header className="site-header relative z-20 bg-white/90 backdrop-blur-xl">
      <div className="mx-auto flex max-w-[1180px] items-center justify-between px-5 py-3.5 lg:px-0">
        <Link href="/" className="flex items-center">
          <BrandMark size="sm" />
        </Link>
        <nav className="hidden items-center gap-8 md:flex" aria-label="주요 메뉴">
          <a href="#service" className="text-[13px] font-bold text-slate-500 transition hover:text-ink">
            서비스
          </a>
          <a href="#how" className="text-[13px] font-bold text-slate-500 transition hover:text-ink">
            이용 방법
          </a>
          {loggedIn ? (
            <button
              type="button"
              onClick={handleLogout}
              className="rounded-full border border-slate-200 bg-white px-4 py-2 text-[13px] font-bold text-slate-600 transition hover:border-rose-300 hover:text-rose-500"
            >
              로그아웃
            </button>
          ) : (
            <Link
              href="/login"
              className="rounded-full border border-slate-200 bg-white px-4 py-2 text-[13px] font-bold text-slate-600 transition hover:border-[#2457d6] hover:text-[#2457d6]"
            >
              로그인
            </Link>
          )}
          <Link
            href={loggedIn ? "/dashboard" : "/signup"}
            className="group flex items-center gap-2 rounded-full bg-[#2457d6] px-4 py-2.5 text-[13px] font-extrabold text-white shadow-[0_8px_18px_rgba(36,87,214,.2)] transition hover:-translate-y-0.5 hover:bg-[#1949c1]"
          >
            {loggedIn ? "대시보드로 이동" : "내 맞춤 혜택 진단"}
            <ArrowRight size={14} className="transition group-hover:translate-x-0.5" />
          </Link>
        </nav>
        <button
          className="rounded-xl p-2 text-slate-600 md:hidden"
          aria-label={mobileOpen ? "메뉴 닫기" : "메뉴 열기"}
          onClick={() => setMobileOpen(!mobileOpen)}
        >
          {mobileOpen ? <X size={21} /> : <Menu size={21} />}
        </button>
      </div>
      {mobileOpen && (
        <div className="absolute left-4 right-4 top-[68px] rounded-2xl border border-slate-100 bg-white p-3 shadow-xl md:hidden">
          <div className="grid gap-1">
            <a href="#service" onClick={() => setMobileOpen(false)} className="rounded-xl px-3 py-3 text-sm font-bold text-slate-600 hover:bg-slate-50">
              서비스
            </a>
            <a href="#how" onClick={() => setMobileOpen(false)} className="rounded-xl px-3 py-3 text-sm font-bold text-slate-600 hover:bg-slate-50">
              이용 방법
            </a>
            {loggedIn ? (
              <button
                type="button"
                onClick={() => {
                  setMobileOpen(false);
                  handleLogout();
                }}
                className="rounded-xl px-3 py-3 text-left text-sm font-bold text-slate-600 hover:bg-slate-50"
              >
                로그아웃
              </button>
            ) : (
              <Link href="/login" onClick={() => setMobileOpen(false)} className="rounded-xl px-3 py-3 text-sm font-bold text-slate-600 hover:bg-slate-50">
                로그인
              </Link>
            )}
            <Link
              href={loggedIn ? "/dashboard" : "/signup"}
              onClick={() => setMobileOpen(false)}
              className="mt-1 rounded-xl bg-[#2457d6] px-3 py-3 text-center text-sm font-extrabold text-white"
            >
              {loggedIn ? "대시보드로 이동" : "내 맞춤 혜택 진단"}
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
