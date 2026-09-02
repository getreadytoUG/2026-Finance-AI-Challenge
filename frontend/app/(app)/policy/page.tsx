"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Banknote, Calendar, ChevronRight, Heart, MapPin, MessageCircle, Search } from "lucide-react";
import { DashboardLayout } from "@/components/DashboardLayout";
import Pagination from "@/components/Pagination";
import PolicyChatDrawer from "@/components/PolicyChatDrawer";
import PolicyDetailLink from "@/components/PolicyDetailLink";
import type { PolicyQaTarget } from "@/components/PolicyQaChatPanel";
import { callTool, getMe, type UserProfile } from "@/lib/api";
import { krwToManwon } from "@/lib/profileOptions";

const PAGE_SIZE = 10;

type PolicyOption = {
  policy_key: string;
  policy_name: string;
  benefit_description: string;
  application_period: string;
  reference_url: string;
  is_newlywed_policy: boolean;
};

type PolicyMatchOutput = {
  options: PolicyOption[];
};

// 카드마다 전부 같은 진한 파랑이면 단조로워 보인다는 피드백 반영 — 3색을 순서대로
// 돌려쓴다(연한 배경 + 진한 텍스트 조합, globals.css의 policy-list-icon 팔레트와
// 동일한 색상을 재사용해 앱 전체 톤과 맞춘다).
const CARD_COLOR_VARIANTS = [
  { icon: "blue", buttonBg: "bg-[#e8f0ff]", buttonText: "text-[#2457d6]", buttonHover: "hover:bg-[#d7e6ff]" },
  { icon: "violet", buttonBg: "bg-[#efedff]", buttonText: "text-[#6252d7]", buttonHover: "hover:bg-[#e1ddff]" },
  { icon: "mint", buttonBg: "bg-[#e5f8f4]", buttonText: "text-[#159c8d]", buttonHover: "hover:bg-[#d2f1ea]" },
] as const;

function ProfileSummaryChip({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2.5 rounded-xl bg-[#f7f9fc] px-4 py-3">
      <span className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-white text-[#2457d6]">{icon}</span>
      <div>
        <div className="text-[10px] font-bold text-slate-400">{label}</div>
        <div className="text-[13px] font-extrabold text-ink">{value}</div>
      </div>
    </div>
  );
}

// 2026-09-01 UPGRADE.md 반영("정책 매칭 폐쇄") 후, 같은 날 사용자 재지시로 한 번 더
// 단순화됨: "정책 매칭" 탭이라는 상위 개념 자체가 폐기되면서, 이 페이지는 더 이상
// 탭 스위처를 갖지 않는다("내 맞춤 정책 보기"/"혼인신고 계산기"가 각자 독립된
// 사이드바 탭으로 분리됨 — 혼인신고 계산기는 app/(app)/marriage/page.tsx 참고).
// 이 페이지 자체도 폼+버튼 없이, 내 정보를 먼저 보여주고 그에 해당하는 모든 정책을
// 바로 나열하는 화면으로 단순화했다(전에 있던 "금융 정책 찾기" 버튼 제거).
export default function PolicyPage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [result, setResult] = useState<PolicyMatchOutput | null>(null);
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [chatTarget, setChatTarget] = useState<PolicyQaTarget | null>(null);
  const [chatOpen, setChatOpen] = useState(false);

  function openChat(option: PolicyOption) {
    setChatTarget({ policy_key: option.policy_key, policy_name: option.policy_name });
    setChatOpen(true);
  }

  function closeChat() {
    setChatOpen(false);
    // 슬라이드 아웃 애니메이션(PolicyChatDrawer의 duration-300)이 끝날 때까지는
    // item을 들고 있어야 사라지는 동안 내용이 먼저 비워지지 않는다.
    setTimeout(() => setChatTarget(null), 300);
  }

  useEffect(() => {
    const token = localStorage.getItem("token") ?? "";
    getMe(token)
      .then((me) => {
        setProfile(me);
        if (me.age == null || me.annual_income_krw == null || me.region == null) {
          setLoading(false);
          return null;
        }
        return callTool<PolicyMatchOutput>(token, "policy_matcher", {
          age: me.age,
          is_married: me.is_married ?? false,
          annual_income_krw: me.annual_income_krw,
          spouse_annual_income_krw: me.is_married && me.spouse_annual_income_krw != null ? me.spouse_annual_income_krw : null,
          region: me.region,
          has_disability: me.has_disability,
          is_veteran: me.is_veteran,
        });
      })
      .then((output) => {
        if (output) setResult(output);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "요청이 실패했습니다."))
      .finally(() => setLoading(false));
  }, []);

  const totalPages = result ? Math.max(1, Math.ceil(result.options.length / PAGE_SIZE)) : 1;
  const pageOptions = result ? result.options.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE) : [];
  const profileIncomplete = profile != null && (profile.age == null || profile.annual_income_krw == null || profile.region == null);

  return (
    <DashboardLayout eyebrow="MY POLICIES" title="내 맞춤 정책 보기">
      {profile && (
        <div className="mb-6 grid gap-3 rounded-[22px] border border-slate-200/80 bg-white p-5 sm:grid-cols-4">
          <ProfileSummaryChip icon={<Calendar size={14} />} label="나이" value={profile.age != null ? `${profile.age}세` : "-"} />
          <ProfileSummaryChip icon={<Heart size={14} />} label="혼인 여부" value={profile.is_married ? "기혼" : "미혼"} />
          <ProfileSummaryChip
            icon={<Banknote size={14} />}
            label="연소득"
            value={profile.annual_income_krw != null ? `${krwToManwon(profile.annual_income_krw).toLocaleString()}만원` : "-"}
          />
          <ProfileSummaryChip icon={<MapPin size={14} />} label="거주 지역" value={profile.region ?? "-"} />
        </div>
      )}

      {profileIncomplete && (
        <div className="mb-6 flex items-center justify-between rounded-2xl border border-[#cddafb] bg-[#eef3ff] p-5 text-[13px] font-bold text-[#2457d6]">
          나이·소득·지역을 입력하면 맞춤 정책을 바로 보여드려요.
          <Link href="/profile" className="inline-flex items-center gap-1 underline">
            내 정보 입력하러 가기 <ChevronRight size={13} />
          </Link>
        </div>
      )}

      {error && <p className="mb-4 text-[13px] font-bold text-rose-500">{error}</p>}
      {loading && <p className="mb-4 text-[13px] text-slate-400">저장된 프로필 기준으로 맞춤 정책을 찾는 중...</p>}

      {!loading &&
        result &&
        (result.options.length === 0 ? (
          <p className="text-[13px] font-bold text-slate-400">지금 신청 가능한 금융 정책을 찾지 못했습니다.</p>
        ) : (
          <>
            <div className="grid gap-3">
              {pageOptions.map((option, i) => {
                const variant = CARD_COLOR_VARIANTS[i % CARD_COLOR_VARIANTS.length];
                return (
                  <div key={i} className="flex flex-col gap-4 rounded-2xl border border-slate-200/80 bg-white p-5 sm:flex-row sm:items-center">
                    <span className={`policy-list-icon ${variant.icon}`}>
                      <Search size={19} />
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        {option.is_newlywed_policy && (
                          <span className="policy-status available">
                            <span />
                            신혼부부
                          </span>
                        )}
                        <span className="text-[15px] font-extrabold tracking-[-.03em] text-ink">{option.policy_name}</span>
                      </div>
                      <p className="mt-2 text-[12px] leading-5 text-slate-500">{option.benefit_description}</p>
                      <div className="mt-2 text-[11px] font-semibold text-slate-400">신청 기간 {option.application_period}</div>
                      <PolicyDetailLink url={option.reference_url} className="mt-2" />
                    </div>
                    <button
                      type="button"
                      onClick={() => openChat(option)}
                      className={`inline-flex shrink-0 items-center justify-center gap-2 rounded-xl px-5 py-3.5 text-[13px] font-extrabold transition hover:-translate-y-0.5 sm:self-stretch ${variant.buttonBg} ${variant.buttonText} ${variant.buttonHover}`}
                    >
                      <MessageCircle size={16} /> AI에게 물어보기
                    </button>
                  </div>
                );
              })}
            </div>
            <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
          </>
        ))}

      <PolicyChatDrawer item={chatTarget} open={chatOpen} onClose={closeChat} />
    </DashboardLayout>
  );
}
