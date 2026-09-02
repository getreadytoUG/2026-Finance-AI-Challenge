// 인디고 브리핑: 공개 화면은 탐색형 헤더, 앱 화면은 동일한 mark와 프로필 액션으로 연결한다.
"use client";

import { ArrowRight, Bell, ChevronDown, Menu, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
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

  function handleLogout() {
    localStorage.removeItem("token");
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
          {/* 예전엔 로그인 상태면 이 랜딩 페이지 자체를 건너뛰고 /dashboard로
              리다이렉트해서 별도 링크가 필요 없었다 — 이제 로그인해도 이 페이지가
              먼저 뜨므로, 로그인 후 화면(대시보드)으로 들어가는 진입점을 헤더에
              따로 둔다(사용자 요청, 2026-09-02). 비로그인 상태로 눌러도 기존
              AppShell의 인증 가드가 알아서 /login으로 돌려보낸다. */}
          <Link href="/dashboard" className="text-[13px] font-bold text-slate-500 transition hover:text-ink">
            대시보드
          </Link>
          <a href="#how" className="text-[13px] font-bold text-slate-500 transition hover:text-ink">
            이용 방법
          </a>
          <Link
            href="/login"
            className="rounded-full border border-slate-200 bg-white px-4 py-2 text-[13px] font-bold text-slate-600 transition hover:border-[#2457d6] hover:text-[#2457d6]"
          >
            로그인
          </Link>
          <Link
            href="/signup"
            className="group flex items-center gap-2 rounded-full bg-[#2457d6] px-4 py-2.5 text-[13px] font-extrabold text-white shadow-[0_8px_18px_rgba(36,87,214,.2)] transition hover:-translate-y-0.5 hover:bg-[#1949c1]"
          >
            내 맞춤 혜택 진단 <ArrowRight size={14} className="transition group-hover:translate-x-0.5" />
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
            <Link href="/dashboard" onClick={() => setMobileOpen(false)} className="rounded-xl px-3 py-3 text-sm font-bold text-slate-600 hover:bg-slate-50">
              대시보드
            </Link>
            <a href="#how" onClick={() => setMobileOpen(false)} className="rounded-xl px-3 py-3 text-sm font-bold text-slate-600 hover:bg-slate-50">
              이용 방법
            </a>
            <Link href="/login" className="rounded-xl px-3 py-3 text-sm font-bold text-slate-600 hover:bg-slate-50">
              로그인
            </Link>
            <Link href="/signup" className="mt-1 rounded-xl bg-[#2457d6] px-3 py-3 text-center text-sm font-extrabold text-white">
              내 맞춤 혜택 진단
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
