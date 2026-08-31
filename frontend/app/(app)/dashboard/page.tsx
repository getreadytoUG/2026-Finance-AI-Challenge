"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, ArrowUpRight, Bell, CalendarClock, ChevronRight, PiggyBank, Search, Sparkles, TrendingUp } from "lucide-react";
import { DashboardLayout, SectionLabel } from "@/components/DashboardLayout";
import PolicyDetailLink from "@/components/PolicyDetailLink";
import StatCard from "@/components/StatCard";
import { callTool, getMe, getRecommendations, listSavingsLinkedBenefits, type Recommendation } from "@/lib/api";

type PolicyOption = {
  policy_name: string;
  benefit_description: string;
  application_period: string;
  reference_url: string;
  is_newlywed_policy: boolean;
};

type PolicyMatchOutput = {
  options: PolicyOption[];
};

export default function DashboardPage() {
  const [label, setLabel] = useState("회원님");
  const [profileComplete, setProfileComplete] = useState(true);
  const [policies, setPolicies] = useState<PolicyOption[]>([]);
  const [linkedTotal, setLinkedTotal] = useState(0);
  const [unreadCount, setUnreadCount] = useState(0);
  const [recentRecs, setRecentRecs] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("token") ?? "";
    getMe(token)
      .then((profile) => {
        setLabel(profile.email.split("@")[0]);
        const complete = profile.age != null && profile.region != null && profile.annual_income_krw != null;
        setProfileComplete(complete);
        if (!complete) return null;
        return callTool<PolicyMatchOutput>(token, "policy_matcher", {
          age: profile.age,
          is_married: profile.is_married,
          annual_income_krw: profile.annual_income_krw,
          spouse_annual_income_krw: profile.spouse_annual_income_krw,
          region: profile.region,
        });
      })
      .then((res) => {
        if (res) setPolicies(res.options);
      })
      .catch(() => {})
      .finally(() => setLoading(false));

    listSavingsLinkedBenefits(token)
      .then((res) => setLinkedTotal(res.total_monthly_benefit_krw))
      .catch(() => {});

    getRecommendations(token)
      .then((res) => {
        setUnreadCount(res.unread_count);
        setRecentRecs(res.recommendations.slice(0, 3));
      })
      .catch(() => {});
  }, []);

  if (loading) return null;

  return (
    <DashboardLayout
      eyebrow="MY POLICY BRIEFING"
      title={`${label}님, 오늘의 혜택을 정리했어요.`}
      action={
        <Link
          href="/policy"
          className="group inline-flex items-center gap-2 rounded-xl bg-[#2457d6] px-4 py-3 text-[12px] font-extrabold text-white shadow-[0_10px_20px_rgba(36,87,214,.18)] transition hover:-translate-y-0.5 hover:bg-[#1949c1]"
        >
          정책 다시 찾기 <ArrowRight size={15} className="transition group-hover:translate-x-1" />
        </Link>
      }
    >
      {!profileComplete && (
        <div className="mb-6 rounded-2xl border border-[#cddafb] bg-[#eef3ff] p-5 text-[13px] font-bold text-[#2457d6]">
          내 정보에서 나이·소득·지역을 입력하면 맞춤 정책 브리핑을 보여드려요.{" "}
          <Link href="/profile" className="underline">
            내 정보 입력하러 가기
          </Link>
        </div>
      )}

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.55fr)_minmax(300px,.75fr)]">
        <section className="brief-hero relative overflow-hidden rounded-[24px] bg-[#0d1b36] px-6 py-7 text-white sm:px-8 sm:py-9">
          <div className="absolute inset-0 bg-[linear-gradient(105deg,rgba(13,27,54,.96),rgba(36,87,214,.68))]" />
          <div className="relative max-w-[560px]">
            <div className="mb-5 flex items-center gap-2 text-[10px] font-extrabold uppercase tracking-[.2em] text-[#9cc5ff]">
              <Sparkles size={13} /> MATCHING COMPLETE
            </div>
            <h2 className="text-[25px] font-extrabold leading-[1.25] tracking-[-.06em] sm:text-[31px]">
              지금 신청 가능한 정책
              <br />
              <span className="text-[#9cc5ff]">{policies.length}개</span>를 찾았어요.
            </h2>
            <p className="mt-4 max-w-[450px] text-[13px] leading-6 text-blue-100/75">저장된 프로필 기준으로 지금 조건에 가장 가까운 정책부터 골랐어요.</p>
          </div>
          <div className="relative mt-8 flex items-center gap-3 border-t border-white/10 pt-5 text-[11px] font-semibold text-blue-100/70">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-white/10">
              <CalendarClock size={15} />
            </span>{" "}
            지금 바로 다시 조회 가능
            <Link href="/ai-search" className="ml-auto inline-flex items-center gap-1 font-extrabold text-white hover:text-[#9cc5ff]">
              AI 리포트 보기 <ChevronRight size={13} />
            </Link>
          </div>
        </section>
        <section className="rounded-[24px] border border-slate-200/80 bg-white p-6 shadow-[0_14px_38px_rgba(28,50,88,.05)]">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-[10px] font-extrabold uppercase tracking-[.16em] text-[#2457d6]">SAVINGS</div>
              <h2 className="mt-2 text-[17px] font-extrabold tracking-[-.04em]">저축플랜</h2>
            </div>
            <Link href="/savings" className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-50 hover:text-[#2457d6]" aria-label="저축플랜 자세히 보기">
              <ArrowUpRight size={16} />
            </Link>
          </div>
          {linkedTotal > 0 ? (
            <>
              <div className="mt-8 flex items-end gap-2">
                <span className="text-[30px] font-extrabold tracking-[-.06em] text-ink">{linkedTotal.toLocaleString()}</span>
                <span className="mb-1 text-[13px] font-extrabold text-[#2457d6]">원 / 월</span>
              </div>
              <div className="mt-2 text-[11px] font-semibold text-slate-500">정책 혜택이 저축 목표에 반영돼 있어요.</div>
              <div className="mt-7 rounded-xl bg-[#f4f8fc] p-3.5">
                <div className="flex items-center gap-2 text-[11px] font-bold text-slate-500">
                  <TrendingUp size={14} className="text-[#1eb8a6]" /> 저축플랜에서 실제 필요 금액을 다시 계산해보세요
                </div>
              </div>
            </>
          ) : (
            <div className="mt-8">
              <PiggyBank size={26} className="text-[#2457d6]" />
              <p className="mt-3 text-[13px] font-bold text-slate-500">아직 저축플랜에 반영한 정책이 없어요.</p>
              <Link href="/savings" className="mt-4 flex items-center justify-between rounded-xl bg-[#f0f4ff] px-3.5 py-3 text-[11px] font-extrabold text-[#2457d6]">
                저축플랜 만들어보기 <ArrowRight size={14} />
              </Link>
            </div>
          )}
        </section>
      </div>

      <div className="mt-8 grid gap-3 sm:grid-cols-3">
        <StatCard label="신청 가능한 정책" value={`${policies.length}개`} detail="지금 조건 기준" tone="blue" />
        <StatCard label="연결된 정책 혜택" value={linkedTotal > 0 ? `월 ${linkedTotal.toLocaleString()}원` : "0원"} detail="저축플랜에 반영됨" tone="mint" />
        <StatCard label="안 읽은 추천" value={`${unreadCount}개`} detail="매일 새벽 자동 매칭" tone="violet" />
      </div>

      <div className="mt-10 grid gap-8 xl:grid-cols-[minmax(0,1.55fr)_minmax(300px,.75fr)]">
        <section>
          <SectionLabel
            action={
              <Link href="/policy" className="text-[11px] font-extrabold text-[#2457d6]">
                전체 보기 <ChevronRight className="inline" size={13} />
              </Link>
            }
          >
            나에게 맞는 정책
          </SectionLabel>
          {policies.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-[13px] font-bold text-slate-400">
              아직 매칭된 정책이 없어요.{" "}
              <Link href="/policy" className="text-[#2457d6]">
                정책 매칭 하러 가기
              </Link>
            </div>
          ) : (
            <div className="grid gap-3">
              {policies.slice(0, 3).map((policy, i) => (
                <Link
                  href="/policy"
                  key={i}
                  className="group flex items-center gap-4 rounded-2xl border border-slate-200/80 bg-white p-4 shadow-[0_8px_24px_rgba(28,50,88,.035)] transition hover:-translate-y-0.5 hover:border-[#ccdaf8] hover:shadow-[0_14px_30px_rgba(28,50,88,.08)]"
                >
                  <span className="policy-list-icon blue">
                    <Search size={18} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[14px] font-extrabold tracking-[-.03em] text-ink">{policy.policy_name}</span>
                      <span className="policy-status available">
                        <span />
                        신청 가능
                      </span>
                    </div>
                    <div className="mt-1 text-[11px] font-semibold text-slate-400">{policy.benefit_description}</div>
                  </div>
                  <ChevronRight size={17} className="text-slate-300 transition group-hover:translate-x-1 group-hover:text-[#2457d6]" />
                </Link>
              ))}
            </div>
          )}
        </section>
        <section>
          <SectionLabel
            action={
              <Link href="/recommendations" className="text-[11px] font-bold text-slate-400 hover:text-[#2457d6]">
                전체 보기
              </Link>
            }
          >
            최근 추천
          </SectionLabel>
          <div className="rounded-2xl border border-slate-200/80 bg-white p-5">
            {recentRecs.length === 0 ? (
              <div className="flex items-start gap-3">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[#eef3ff] text-[#2457d6]">
                  <Bell size={17} />
                </span>
                <p className="text-[12px] leading-5 text-slate-500">아직 도착한 추천이 없어요. 매일 새벽 프로필 기준으로 새 정책을 찾아드려요.</p>
              </div>
            ) : (
              <div className="grid gap-4">
                {recentRecs.map((rec) => (
                  <div key={rec.id} className="flex items-start gap-3">
                    <span className={`grid h-6 w-6 shrink-0 place-items-center rounded-full border ${rec.is_read ? "border-slate-200 text-transparent" : "border-[#1eb8a6] bg-[#1eb8a6] text-white"}`}>
                      <Bell size={12} />
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className={`text-[12px] font-bold ${rec.is_read ? "text-slate-400" : "text-ink"}`}>{rec.policy_name}</div>
                      <PolicyDetailLink url={rec.reference_url} className="mt-1 text-[11px]" />
                    </div>
                  </div>
                ))}
              </div>
            )}
            {unreadCount > 0 && (
              <div className="mt-5 border-t border-slate-100 pt-4 text-[11px] font-semibold text-slate-400">
                안 읽은 추천 <span className="text-[#2457d6]">{unreadCount}개</span>
              </div>
            )}
          </div>
        </section>
      </div>
    </DashboardLayout>
  );
}
