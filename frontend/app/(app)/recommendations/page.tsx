"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Bell, Clock, MessageCircle } from "lucide-react";
import { getMe, getRecommendations, markRecommendationRead, refreshRecommendations, updateProfile } from "@/lib/api";
import type { Recommendation, UserProfile } from "@/lib/api";
import { OCCUPATION_OPTIONS, manwonToKrw, type OccupationType } from "@/lib/profileOptions";
import { DashboardLayout } from "@/components/DashboardLayout";
import Pagination from "@/components/Pagination";
import PolicyChatDrawer from "@/components/PolicyChatDrawer";
import PolicyDetailLink from "@/components/PolicyDetailLink";
import type { PolicyQaTarget } from "@/components/PolicyQaChatPanel";
import StatusPill from "@/components/StatusPill";
import RecommendationCalendar from "@/components/RecommendationCalendar";
import AiPolicySearchSection from "@/components/AiPolicySearchSection";

const PAGE_SIZE = 10;

function hasCompleteProfile(profile: UserProfile | null): boolean {
  return (
    profile !== null &&
    profile.age !== null &&
    profile.is_married !== null &&
    profile.annual_income_krw !== null &&
    profile.region !== null
  );
}

export default function RecommendationsPage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[] | null>(null);
  const [age, setAge] = useState("29");
  const [isMarried, setIsMarried] = useState(false);
  const [income, setIncome] = useState("4000");
  const [region, setRegion] = useState("서울");
  const [occupation, setOccupation] = useState<OccupationType>("employee");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const searchParams = useSearchParams();
  // 대시보드의 "AI 정책 검색 →" 딥링크가 캘린더가 아니라 바로 이 서브탭으로
  // 떨어지도록 ?view=ai_search 쿼리를 초기값으로 반영한다.
  const [view, setView] = useState<"calendar" | "list" | "ai_search">(
    searchParams.get("view") === "ai_search" ? "ai_search" : "calendar"
  );
  // 2026-09-02 QA에서 발견: "맞춤 정책 추천함" 탭에서 링크가 없는 항목은 클릭해도
  // 더 알아볼 방법이 없었다 — 대시보드와 동일하게 정책별 챗봇으로 폴백한다.
  const [chatTarget, setChatTarget] = useState<PolicyQaTarget | null>(null);
  const [chatOpen, setChatOpen] = useState(false);

  function openChat(target: PolicyQaTarget) {
    setChatTarget(target);
    setChatOpen(true);
  }

  function closeChat() {
    setChatOpen(false);
    setTimeout(() => setChatTarget(null), 300);
  }

  async function loadProfileAndRecommendations() {
    const token = localStorage.getItem("token") ?? "";
    const me = await getMe(token);
    setProfile(me);
    if (hasCompleteProfile(me)) {
      const list = await getRecommendations(token);
      setRecommendations(list.recommendations);
    }
  }

  useEffect(() => {
    loadProfileAndRecommendations().catch((err) => {
      setError(err instanceof Error ? err.message : "불러오기에 실패했습니다.");
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleProfileSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const token = localStorage.getItem("token") ?? "";
    try {
      await updateProfile(token, {
        age: Number(age),
        is_married: isMarried,
        annual_income_krw: manwonToKrw(Number(income)),
        region,
        occupation,
      });
      await loadProfileAndRecommendations();
    } catch (err) {
      setError(err instanceof Error ? err.message : "프로필 저장에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }

  async function handleRefresh() {
    setError(null);
    setLoading(true);
    const token = localStorage.getItem("token") ?? "";
    try {
      await refreshRecommendations(token);
      const list = await getRecommendations(token);
      setRecommendations(list.recommendations);
      setPage(1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "추천 갱신에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }

  async function handleItemClick(rec: Recommendation) {
    if (rec.is_read) return;
    const token = localStorage.getItem("token") ?? "";
    try {
      await markRecommendationRead(token, rec.id);
      setRecommendations((prev) => (prev ? prev.map((r) => (r.id === rec.id ? { ...r, is_read: true } : r)) : prev));
    } catch {
      // 읽음 처리 실패는 조용히 무시 — 목록 자체는 이미 정상 표시되어 있다.
    }
  }

  return (
    <DashboardLayout
      eyebrow="POLICY CALENDAR"
      title="정책 달력"
      action={
        hasCompleteProfile(profile) ? (
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="rounded-xl bg-[#2457d6] px-4 py-3 text-[12px] font-extrabold text-white shadow-[0_10px_20px_rgba(36,87,214,.18)] transition hover:bg-[#1949c1] disabled:opacity-50"
          >
            {loading ? "갱신 중..." : "지금 갱신"}
          </button>
        ) : undefined
      }
    >
      <div className="mb-6 grid gap-3 sm:grid-cols-2">
        <div className="flex items-start gap-3 rounded-2xl border border-slate-200/80 bg-white p-4">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[#eef3ff] text-[#2457d6]">
            <Clock size={17} />
          </span>
          <div>
            <div className="text-[13px] font-extrabold text-ink">매일 새벽 자동 매칭</div>
            <p className="mt-1 text-[12px] leading-5 text-slate-500">저장된 프로필 기준으로 매일 새벽 새로 등록된 정책을 찾아 쌓아둬요.</p>
          </div>
        </div>
        <div className="flex items-start gap-3 rounded-2xl border border-slate-200/80 bg-white p-4">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[#e6f8f5] text-[#159c8d]">
            <Bell size={17} />
          </span>
          <div>
            <div className="text-[13px] font-extrabold text-ink">안 읽은 것만 표시</div>
            <p className="mt-1 text-[12px] leading-5 text-slate-500">확인 안 한 추천은 사이드바 종 아이콘에 숫자로 뜹니다.</p>
          </div>
        </div>
      </div>

      {error && <p className="mb-4 text-[13px] font-bold text-rose-500">{error}</p>}

      {!hasCompleteProfile(profile) && (
        <div className="rounded-[22px] border border-slate-200/80 bg-white p-6">
          <form onSubmit={handleProfileSubmit} className="grid gap-4 sm:grid-cols-2">
            <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
              나이
              <input
                type="number"
                value={age}
                onChange={(e) => setAge(e.target.value)}
                className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
              />
            </label>
            <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
              연소득 (만원)
              <input
                type="number"
                value={income}
                onChange={(e) => setIncome(e.target.value)}
                className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
              />
            </label>
            <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
              지역
              <input
                type="text"
                value={region}
                onChange={(e) => setRegion(e.target.value)}
                className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
              />
            </label>
            <label className="flex items-center gap-2 text-[13px] font-bold text-slate-700">
              <input type="checkbox" checked={isMarried} onChange={(e) => setIsMarried(e.target.checked)} className="h-4 w-4 accent-[#2457d6]" />
              기혼
            </label>
            <div className="sm:col-span-2">
              <div className="mb-2 text-[12px] font-extrabold text-slate-700">직업 구분</div>
              <div className="flex flex-wrap gap-2">
                {OCCUPATION_OPTIONS.map((o) => (
                  <button
                    key={o.value}
                    type="button"
                    onClick={() => setOccupation(o.value)}
                    className={`rounded-lg px-3.5 py-2 text-[11px] font-extrabold transition ${
                      occupation === o.value ? "bg-[#2457d6] text-white" : "bg-[#eef3f9] text-slate-500 hover:bg-[#e3eaf6]"
                    }`}
                  >
                    {o.label}
                  </button>
                ))}
              </div>
            </div>
            <button
              type="submit"
              disabled={loading}
              className="h-12 rounded-xl bg-[#2457d6] text-[13px] font-extrabold text-white shadow-[0_10px_20px_rgba(36,87,214,.18)] transition hover:bg-[#1949c1] disabled:opacity-50 sm:col-span-2"
            >
              {loading ? "저장 중..." : "프로필 저장하고 추천 받기"}
            </button>
          </form>
        </div>
      )}

      {hasCompleteProfile(profile) && (
        <>
          {/* 예전엔 이 탭 스위처 자체가 recommendations.length > 0 뒤에 숨어 있어서,
              배치 추천이 한 번도 안 쌓인 유저는 "지금 갱신"을 누르기 전엔 캘린더도
              AI 정책 검색도 아예 볼 수 없었다 — 근데 이 둘은 recommendations(배치가
              쌓아둔 알림 목록)와 무관하게 자기가 직접 정책을 불러오는 화면이라
              갱신 여부와 상관없이 항상 열려야 한다(사용자 요청, 2026-09-02). "맞춤 정책
              추천함" 탭만 recommendations를 그대로 보여주는 화면이라 비어있으면 그 탭
              안에서만 안내 문구를 보여준다. */}
          {/* 순서/이름 사용자 요청(2026-09-02): 정책 캘린더 | 정책 전체 보기 | 맞춤 정책
              추천함. 마지막 탭은 "정책 리스트"라는 이름이 역할(새벽 배치가 매칭해서
              쌓아두는 알림함이지 라이브 검색이 아님)을 잘 못 드러낸다는 이유로 다시
              바뀌었다. */}
          <div className="mb-6 inline-flex gap-1.5 rounded-xl bg-[#eef3f9] p-1">
            <button
              onClick={() => setView("calendar")}
              className={`rounded-lg px-4 py-2.5 text-[12px] font-extrabold transition ${view === "calendar" ? "bg-white text-[#2457d6] shadow-sm" : "text-slate-500"}`}
            >
              정책 캘린더
            </button>
            <button
              onClick={() => setView("ai_search")}
              className={`rounded-lg px-4 py-2.5 text-[12px] font-extrabold transition ${view === "ai_search" ? "bg-white text-[#2457d6] shadow-sm" : "text-slate-500"}`}
            >
              정책 전체 보기
            </button>
            <button
              onClick={() => setView("list")}
              className={`rounded-lg px-4 py-2.5 text-[12px] font-extrabold transition ${view === "list" ? "bg-white text-[#2457d6] shadow-sm" : "text-slate-500"}`}
            >
              맞춤 정책 추천함
            </button>
          </div>

          {view === "calendar" ? (
            <RecommendationCalendar />
          ) : view === "ai_search" ? (
            <AiPolicySearchSection />
          ) : recommendations === null ? (
            <p className="text-[13px] text-slate-400">불러오는 중...</p>
          ) : recommendations.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-300 p-10 text-center text-[13px] font-bold text-slate-400">
              아직 추천된 정책이 없습니다. &quot;지금 갱신&quot;을 눌러보세요.
            </div>
          ) : (
            <>
              <div className="grid gap-3">
                {recommendations.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE).map((rec) => (
                  <div
                    key={rec.id}
                    onClick={() => handleItemClick(rec)}
                    className="cursor-pointer rounded-2xl border border-slate-200/80 bg-white p-5 transition hover:border-[#cddafb] hover:shadow-[0_14px_30px_rgba(28,50,88,.07)]"
                  >
                    <div className="flex flex-wrap items-center gap-2 text-[15px] font-extrabold text-ink">
                      {rec.policy_name}
                      <StatusPill status={rec.status} />
                      <span
                        className={`rounded-full px-2.5 py-1 text-[10px] font-extrabold ${
                          rec.is_read ? "bg-slate-100 text-slate-400" : "bg-ink text-white"
                        }`}
                      >
                        {rec.is_read ? "읽음" : "안읽음"}
                      </span>
                    </div>
                    <p className="mt-2 text-[12px] leading-5 text-slate-500">{rec.benefit_description}</p>
                    <div className="mt-2 text-[11px] font-semibold text-slate-400">신청 기간 {rec.application_period}</div>
                    {rec.reference_url ? (
                      <PolicyDetailLink url={rec.reference_url} className="mt-2" />
                    ) : (
                      <button
                        type="button"
                        onClick={() => openChat({ policy_key: rec.policy_key, policy_name: rec.policy_name })}
                        className="mt-2 inline-flex items-center gap-1 text-[13px] font-bold text-[#2457d6] hover:underline"
                      >
                        <MessageCircle size={14} /> 이 정책 물어보기
                      </button>
                    )}
                  </div>
                ))}
              </div>
              <Pagination page={page} totalPages={Math.max(1, Math.ceil(recommendations.length / PAGE_SIZE))} onPageChange={setPage} />
            </>
          )}
        </>
      )}

      <PolicyChatDrawer item={chatTarget} open={chatOpen} onClose={closeChat} />
    </DashboardLayout>
  );
}
