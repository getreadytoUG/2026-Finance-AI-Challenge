"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  ArrowUpRight,
  BriefcaseBusiness,
  ChevronRight,
  GraduationCap,
  HeartPulse,
  House,
  PiggyBank,
  ShieldCheck,
  Sparkles,
  WalletCards,
} from "lucide-react";
import { SiteHeader } from "@/components/SiteHeader";
import { BrandMark } from "@/components/BrandMark";
import { isTokenExpired } from "@/lib/api";

// 카테고리/기능 카드는 전부 loggedInPath를 따로 둔다 — 로그인 안 한 방문자에게는
// path(=/signup, 회원가입 유도)를, 이미 로그인한 유저에게는 실제 기능 화면을
// 보여줘야 한다(사용자 요청, 2026-09-02: "다른 기능들 들어갈 때마다 로그인을
// 또 하라고 걸린다" — 로그인 상태여도 이 랜딩 페이지가 먼저 뜨도록 바뀌면서, 카드를
// 누르면 전부 /signup으로만 꽂혀있던 게 이미 로그인된 사람한테도 그대로 적용돼
// 생긴 문제였다). "정책 읽기"/"AI 분석 리포트"는 UPGRADE.md 개편으로 독립 화면이
// 아니라 "정책 달력 > 정책 전체 보기"로 흡수됐으므로 같은 곳으로 보낸다.
const CATEGORIES = [
  { label: "일자리", detail: "취업·창업", icon: BriefcaseBusiness, color: "blue" },
  { label: "주거", detail: "전월세·대출", icon: House, color: "sky" },
  { label: "교육", detail: "학자금·훈련", icon: GraduationCap, color: "violet" },
  { label: "금융·복지", detail: "생활 안정", icon: HeartPulse, color: "mint" },
] as const;
const CATEGORY_LOGGED_IN_PATH = "/recommendations?view=ai_search";

const FEATURE_CARDS = [
  {
    title: "금융 정책 추천",
    detail: "내 조건에 맞는 정책만 모아봐요.",
    icon: WalletCards,
    loggedInPath: "/policy",
    tone: "blue",
  },
  {
    title: "정책 읽기",
    detail: "카테고리·지역별로 전체 정책을 탐색해요.",
    icon: BriefcaseBusiness,
    loggedInPath: "/recommendations?view=ai_search",
    tone: "sky",
  },
  {
    title: "AI 분석 리포트",
    detail: "혜택과 유의사항을 한 번에 확인해요.",
    icon: Sparkles,
    loggedInPath: "/recommendations?view=ai_search",
    tone: "violet",
  },
  {
    title: "저축플랜",
    detail: "목표까지 필요한 금액을 계산해요.",
    icon: PiggyBank,
    loggedInPath: "/savings",
    tone: "mint",
  },
] as const;

const STEPS = [
  { n: "01", title: "프로필 입력", body: "나이, 소득, 지역, 혼인 여부를 알려주면 내게 맞는 정책만 골라드려요." },
  { n: "02", title: "AI가 정책 매칭 & 분석", body: "실제 정책 데이터를 기준으로 적합도·예상 혜택·유의사항을 리포트로 정리해요." },
  { n: "03", title: "저축플랜에 반영", body: "정책 혜택을 목표에 반영해 내가 실제로 더 모아야 할 금액을 계산해요." },
];

// 2026-09-02: 예전엔 로그인 상태면 이 랜딩 페이지를 건너뛰고 바로 /dashboard로
// 리다이렉트했는데, 사용자 요청으로 이제 로그인 여부와 상관없이 누구나 이 페이지를
// 먼저 보게 한다 — 이 페이지가 곧 메인 페이지다. 로그인한 사용자가 기존 대시보드로
// 들어가려면 헤더의 "대시보드로 이동" 버튼(SiteHeader.tsx)을 누르면 된다.
export default function Home() {
  // 카테고리/기능 카드가 로그인 여부와 상관없이 전부 /signup으로 고정돼 있었다 —
  // 로그인 상태여도 이 페이지가 먼저 뜨게 바뀌면서, 이미 로그인한 유저가 다른
  // 기능을 눌러도 회원가입 화면으로 떨어지는(=사실상 다시 로그인/가입을 요구하는
  // 것처럼 보이는) 문제로 이어졌다(사용자 요청, 2026-09-02). SiteHeader.tsx와
  // 동일한 패턴으로 로그인 여부를 확인해 실제 기능 화면으로 보낸다.
  const [loggedIn, setLoggedIn] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("token");
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoggedIn(!!token && !isTokenExpired(token));
  }, []);

  return (
    <div className="landing min-h-screen overflow-hidden bg-[#f7f9fc] text-ink">
      <SiteHeader />
      <section className="hero relative isolate overflow-hidden bg-[#0d1b36] text-white">
        <div className="absolute inset-0 bg-[linear-gradient(100deg,rgba(13,27,54,.94),rgba(36,87,214,.68)_56%,rgba(24,58,145,.9))]" />
        <div className="relative mx-auto grid min-h-[560px] max-w-[1180px] items-center gap-12 px-5 pb-28 pt-20 lg:grid-cols-[1.1fr_.9fr] lg:px-0 lg:pb-32">
          <div className="max-w-[600px] animate-fade-up">
            <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3.5 py-2 text-[11px] font-bold text-blue-100 backdrop-blur-sm">
              <Sparkles size={13} /> AI 기반 정책·저축 통합 매칭
            </div>
            <h1 className="max-w-[650px] text-[39px] font-extrabold leading-[1.15] tracking-[-0.07em] sm:text-[56px]">
              복잡한 청년·신혼부부 정책,
              <br />
              <span className="text-[#9cc5ff]">내 저축 계획으로</span> 바로 연결합니다
            </h1>
            <p className="mt-6 max-w-[490px] text-[15px] leading-7 text-blue-100/85 sm:text-[16px]">
              나이·소득·지역만 입력하면 지금 신청 가능한 정책을 찾아드리고, AI가 분석한 실제 혜택을 저축 목표에 반영해드려요.
            </p>
            <div className="mt-9 flex flex-wrap items-center gap-3">
              <Link
                href={loggedIn ? "/dashboard" : "/signup"}
                style={{ color: "#2457d6" }}
                className="group inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3.5 text-[13px] font-extrabold shadow-[0_14px_30px_rgba(7,21,58,.28)] transition hover:-translate-y-1"
              >
                {loggedIn ? "대시보드로 이동" : "내 맞춤 혜택 진단"} <ArrowRight size={16} className="transition group-hover:translate-x-1" />
              </Link>
              <a href="#how" className="rounded-xl border border-white/25 px-5 py-3.5 text-[13px] font-bold text-white transition hover:bg-white/10">
                어떻게 연결되나요?
              </a>
            </div>
            <div className="mt-8 flex items-center gap-5 text-[11px] font-semibold text-blue-100/65">
              <span className="inline-flex items-center gap-1.5">
                <ShieldCheck size={14} /> 공공 정책 데이터 기반
              </span>
              <span className="h-3 w-px bg-white/20" />
              <span>무료로 시작</span>
            </div>
          </div>
          <div className="relative hidden lg:block">
            <div className="absolute -right-5 -top-12 h-52 w-52 rounded-full bg-[#76d8d0]/15 blur-3xl" />
            <div className="relative ml-auto max-w-[380px] rotate-[2deg] rounded-[26px] border border-white/15 bg-[#f8fbff]/95 p-5 text-ink shadow-[0_26px_70px_rgba(5,20,60,.35)] backdrop-blur-lg">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-[10px] font-extrabold uppercase tracking-[.16em] text-[#2457d6]">Your briefing</div>
                  <div className="mt-1 text-[15px] font-extrabold">오늘의 추천 요약</div>
                </div>
                <span className="grid h-9 w-9 place-items-center rounded-xl bg-[#e5efff] text-[#2457d6]">
                  <Sparkles size={17} />
                </span>
              </div>
              <div className="mt-5 rounded-2xl bg-[#eff4fb] p-4">
                <div className="flex items-center justify-between text-[11px] font-bold text-slate-500">
                  <span>정책 매칭</span>
                  <span className="text-[#2457d6]">실시간</span>
                </div>
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-[#dbe5f4]">
                  <div className="h-full w-[86%] rounded-full bg-[#2457d6]" />
                </div>
                <div className="mt-2 text-[12px] font-extrabold text-ink">프로필 입력 즉시 신청 가능한 정책만 골라요</div>
              </div>
              <div className="mt-4 grid gap-2.5">
                {["AI 분석 리포트", "저축플랜 자동 반영"].map((item, i) => (
                  <div key={item} className="flex items-center gap-3 rounded-xl border border-slate-100 bg-white px-3 py-3">
                    <span className={`grid h-8 w-8 place-items-center rounded-lg ${i ? "bg-[#e6f8f5] text-[#159c8d]" : "bg-[#e8f0ff] text-[#2457d6]"}`}>
                      {i ? <PiggyBank size={15} /> : <Sparkles size={15} />}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-[11px] font-extrabold">{item}</div>
                    </div>
                    <ArrowUpRight size={14} className="text-slate-300" />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
        <div className="absolute bottom-0 left-0 right-0 h-20 bg-[#f7f9fc] [clip-path:polygon(0_45%,100%_0,100%_100%,0_100%)]" />
      </section>

      <section className="relative z-10 mx-auto -mt-12 max-w-[1180px] px-5 lg:px-0">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {CATEGORIES.map(({ label, detail, icon: Icon, color }) => (
            <Link
              key={label}
              href={loggedIn ? CATEGORY_LOGGED_IN_PATH : "/signup"}
              className="group rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_15px_40px_rgba(28,50,88,.08)] transition hover:-translate-y-1 hover:shadow-[0_20px_44px_rgba(28,50,88,.13)]"
            >
              <span className={`category-icon ${color}`}>
                <Icon size={18} strokeWidth={2.1} />
              </span>
              <div className="mt-5 text-[14px] font-extrabold tracking-[-.04em] text-ink">{label}</div>
              <div className="mt-1 text-[11px] font-semibold text-slate-400">{detail} 지원 정책</div>
              <ChevronRight size={15} className="mt-4 text-slate-300 transition group-hover:translate-x-1 group-hover:text-[#2457d6]" />
            </Link>
          ))}
        </div>
      </section>

      <section id="service" className="mx-auto max-w-[1180px] px-5 pb-24 pt-28 lg:px-0">
        <div className="mb-10 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <div className="section-kicker">OUR SERVICE</div>
            <h2 className="mt-2 text-[28px] font-extrabold tracking-[-.06em] sm:text-[36px]">정책과 저축을 하나로 연결합니다</h2>
          </div>
          <p className="max-w-[310px] text-[13px] leading-6 text-slate-500">
            찾는 데서 끝나지 않도록,
            <br />
            내 삶의 다음 계획까지 이어드려요.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURE_CARDS.map(({ title, detail, icon: Icon, loggedInPath, tone }) => (
            <Link
              key={title}
              href={loggedIn ? loggedInPath : "/signup"}
              className="group relative min-h-[190px] overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-6 transition hover:-translate-y-1 hover:border-[#cddafb] hover:shadow-[0_18px_42px_rgba(28,50,88,.1)]"
            >
              <span className={`service-icon ${tone}`}>
                <Icon size={18} />
              </span>
              <div className="mt-8 text-[16px] font-extrabold tracking-[-.04em]">{title}</div>
              <p className="mt-2 text-[12px] leading-5 text-slate-500">{detail}</p>
              <ArrowUpRight
                size={17}
                className="absolute bottom-6 right-6 text-slate-300 transition group-hover:-translate-y-1 group-hover:translate-x-1 group-hover:text-[#2457d6]"
              />
            </Link>
          ))}
        </div>
      </section>

      <section id="how" className="relative overflow-hidden bg-[#203f8c] text-white">
        <div className="absolute right-[-10%] top-[-25%] h-[520px] w-[520px] rounded-full border border-white/5" />
        <div className="relative mx-auto max-w-[1180px] px-5 py-24 lg:px-0">
          <div className="text-center">
            <div className="text-[10px] font-extrabold uppercase tracking-[.22em] text-[#9cc5ff]">HOW IT WORKS</div>
            <h2 className="mt-3 text-[30px] font-extrabold tracking-[-.06em]">어떻게 연결되나요?</h2>
            <p className="mt-3 text-[13px] text-blue-100/75">가입부터 저축 계획까지 3단계로 간소화했어요.</p>
          </div>
          <div className="mt-14 grid gap-4 lg:grid-cols-3">
            {STEPS.map((item) => (
              <div key={item.n} className="relative rounded-2xl border border-white/15 bg-white/[.06] p-7 backdrop-blur-sm">
                <div className="flex items-center gap-4">
                  <span className="text-[12px] font-extrabold text-[#8fbaff]">{item.n}</span>
                  <div className="h-px flex-1 bg-white/15" />
                </div>
                <h3 className="mt-8 text-[18px] font-extrabold">{item.title}</h3>
                <p className="mt-3 text-[13px] leading-6 text-blue-100/70">{item.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-[1180px] px-5 py-20 lg:px-0">
        <div className="flex flex-col items-start justify-between gap-7 rounded-[26px] bg-[linear-gradient(105deg,#2457d6,#453fe0)] px-7 py-9 text-white shadow-[0_22px_45px_rgba(36,87,214,.2)] sm:flex-row sm:items-center sm:px-10">
          <div>
            <div className="text-[10px] font-extrabold uppercase tracking-[.18em] text-blue-100">START WITH YOUR PLAN</div>
            <h2 className="mt-3 text-[23px] font-extrabold tracking-[-.05em] sm:text-[28px]">내가 받을 수 있는 정책 혜택은 얼마일까요?</h2>
            <p className="mt-2 text-[13px] text-blue-100">가입하고 프로필만 입력하면 바로 맞춤 정책과 저축 계획을 확인할 수 있어요.</p>
          </div>
          <Link
            href={loggedIn ? "/dashboard" : "/signup"}
            className="group flex shrink-0 items-center gap-3 rounded-xl bg-white px-5 py-3.5 text-[13px] font-extrabold text-[#2457d6] transition hover:-translate-y-1"
          >
            {loggedIn ? "대시보드로 이동" : "무료로 시작하기"} <ArrowRight size={16} className="transition group-hover:translate-x-1" />
          </Link>
        </div>
      </section>

      <footer className="border-t border-slate-200 bg-[#0d1b36] text-white">
        <div className="mx-auto flex max-w-[1180px] flex-col justify-between gap-10 px-5 py-12 sm:flex-row lg:px-0">
          <div>
            <BrandMark size="sm" />
            <p className="mt-4 text-[12px] leading-6 text-slate-400">
              공공 정책 데이터를 기반으로
              <br />
              개인 맞춤 정책 매칭과 저축 계획을 제공합니다.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-12 text-[12px]">
            <div>
              <div className="mb-3 font-extrabold text-white">서비스</div>
              <div className="grid gap-2 text-slate-400">
                <Link href={loggedIn ? "/policy" : "/signup"}>내 맞춤 정책 보기</Link>
                <Link href={loggedIn ? "/savings" : "/signup"}>저축플랜</Link>
                <Link href={loggedIn ? "/dashboard" : "/login"}>{loggedIn ? "대시보드" : "로그인"}</Link>
              </div>
            </div>
            <div>
              <div className="mb-3 font-extrabold text-white">고객지원</div>
              <div className="grid gap-2 text-slate-400">
                <span>공지사항 준비 중</span>
                <span>자주 묻는 질문 준비 중</span>
              </div>
            </div>
          </div>
        </div>
        <div className="border-t border-white/10">
          <div className="mx-auto max-w-[1180px] px-5 py-5 text-[11px] text-slate-500 lg:px-0">
            © 2026 청년/신혼부부 금융 도우미. 정책 정보는 각 기관의 공고를 확인해 주세요.
          </div>
        </div>
      </footer>
    </div>
  );
}
