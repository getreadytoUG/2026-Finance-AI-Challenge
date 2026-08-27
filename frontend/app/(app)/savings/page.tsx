"use client";

import { useEffect, useState } from "react";
import { CircleHelp, Target, TrendingUp } from "lucide-react";
import { callTool, getMe, listSavingsLinkedBenefits, unlinkSavingsBenefit, type LinkedBenefit } from "@/lib/api";
import { DashboardLayout } from "@/components/DashboardLayout";
import SubscriptionsSection from "./SubscriptionsSection";
import CardsSection from "./CardsSection";

type SavingsAllocation = {
  category: string;
  monthly_amount_krw: number;
};

type SavingsPlanOutput = {
  allocations: SavingsAllocation[];
  monthly_required_krw: number;
  linked_monthly_benefit_krw: number;
  feasibility_warning: string | null;
};

const SUB_TABS = [
  { key: "plan", label: "저축플랜" },
  { key: "subscriptions", label: "구독료 리포트" },
  { key: "cards", label: "카드소비 리포트" },
] as const;

type SubTabKey = (typeof SUB_TABS)[number]["key"];

function SavingsPlanSection() {
  const [monthlyIncome, setMonthlyIncome] = useState("3000000");
  const [goalAmount, setGoalAmount] = useState("12000000");
  const [goalMonths, setGoalMonths] = useState("12");
  const [result, setResult] = useState<SavingsPlanOutput | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [linkedBenefits, setLinkedBenefits] = useState<LinkedBenefit[]>([]);

  useEffect(() => {
    const token = localStorage.getItem("token") ?? "";
    getMe(token)
      .then((profile) => {
        if (profile.annual_income_krw != null) {
          setMonthlyIncome(String(Math.round(profile.annual_income_krw / 12)));
        }
      })
      .catch(() => {});
    listSavingsLinkedBenefits(token)
      .then((res) => setLinkedBenefits(res.items))
      .catch(() => {});
  }, []);

  async function handleRemoveLinkedBenefit(id: number) {
    const token = localStorage.getItem("token") ?? "";
    try {
      await unlinkSavingsBenefit(token, id);
      setLinkedBenefits((prev) => prev.filter((b) => b.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "정책 혜택을 제거하지 못했습니다.");
    }
  }

  const linkedBenefitTotal = linkedBenefits.reduce((sum, b) => sum + b.estimated_monthly_benefit_krw, 0);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    setLoading(true);
    const token = localStorage.getItem("token") ?? "";
    try {
      const output = await callTool<SavingsPlanOutput>(token, "savings_planner", {
        monthly_income_krw: Number(monthlyIncome),
        goal_amount_krw: Number(goalAmount),
        goal_months: Number(goalMonths),
      });
      setResult(output);
    } catch (err) {
      setError(err instanceof Error ? err.message : "요청이 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      {linkedBenefits.length > 0 && (
        <div className="mb-5 rounded-2xl border border-slate-200/80 bg-white p-5">
          <div className="mb-3 text-[13px] font-extrabold text-ink">연결된 정책 혜택 · 월 {linkedBenefitTotal.toLocaleString()}원</div>
          <div className="flex flex-wrap gap-1.5">
            {linkedBenefits.map((b) => (
              <span key={b.id} className="inline-flex items-center gap-1.5 rounded-full border border-[#2457d6] bg-[#eef3ff] px-3 py-1.5 text-[12px] font-bold text-[#2457d6]">
                {b.policy_name} · {b.estimated_monthly_benefit_krw.toLocaleString()}원/월
                <button type="button" onClick={() => handleRemoveLinkedBenefit(b.id)} aria-label={`${b.policy_name} 혜택 제거`} className="text-[#2457d6]/70 hover:text-[#2457d6]">
                  ×
                </button>
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="rounded-[22px] border border-slate-200/80 bg-white p-6">
        <form onSubmit={handleSubmit} className="grid gap-4 sm:grid-cols-3">
          <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
            월급 (원)
            <input
              type="number"
              value={monthlyIncome}
              onChange={(e) => setMonthlyIncome(e.target.value)}
              className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
            />
          </label>
          <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
            목표 금액 (원)
            <input
              type="number"
              value={goalAmount}
              onChange={(e) => setGoalAmount(e.target.value)}
              className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
            />
          </label>
          <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
            목표 기간 (개월)
            <input
              type="number"
              value={goalMonths}
              onChange={(e) => setGoalMonths(e.target.value)}
              className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
            />
          </label>
          <button
            type="submit"
            disabled={loading}
            className="h-12 rounded-xl bg-[#2457d6] text-[13px] font-extrabold text-white shadow-[0_10px_20px_rgba(36,87,214,.18)] transition hover:bg-[#1949c1] disabled:opacity-50 sm:col-span-3"
          >
            {loading ? "계산 중..." : "저축 플랜 만들기"}
          </button>
        </form>
      </div>

      {error && <p className="mt-4 text-[13px] font-bold text-rose-500">{error}</p>}

      {result && (
        <div className="mt-6 grid gap-5 xl:grid-cols-[1.4fr_.8fr]">
          <section className="relative overflow-hidden rounded-[24px] bg-[#0d1b36] p-7 text-white sm:p-9">
            <div className="absolute inset-0 bg-[linear-gradient(100deg,#0d1b36_12%,rgba(13,27,54,.86)_54%,rgba(13,27,54,.35))]" />
            <div className="relative">
              <div className="text-[10px] font-extrabold uppercase tracking-[.2em] text-[#9cc5ff]">GOAL LEDGER</div>
              <h2 className="mt-3 text-[26px] font-extrabold tracking-[-.06em] sm:text-[32px]">
                월 <span className="text-[#9cc5ff]">{result.monthly_required_krw.toLocaleString()}원</span>씩 모으면 목표를 채워요.
              </h2>
              <p className="mt-4 text-[12px] leading-6 text-blue-100/70">
                {result.linked_monthly_benefit_krw > 0
                  ? `정책 혜택 월 ${result.linked_monthly_benefit_krw.toLocaleString()}원을 반영해 실제로 더 모아야 할 금액을 계산했어요.`
                  : "정책 혜택을 저축플랜에 반영하면 실제 필요 금액이 더 줄어들 수 있어요."}
              </p>
              <div className="mt-8 grid max-w-[480px] grid-cols-2 gap-3">
                <div className="rounded-xl bg-white/10 p-3.5">
                  <div className="text-[10px] font-bold text-blue-100/60">월 필요 저축액</div>
                  <div className="mt-2 text-[16px] font-extrabold">{result.monthly_required_krw.toLocaleString()}원</div>
                </div>
                <div className="rounded-xl bg-[#1eb8a6]/15 p-3.5">
                  <div className="text-[10px] font-bold text-[#baf1e9]/70">정책 혜택 반영</div>
                  <div className="mt-2 text-[16px] font-extrabold text-[#baf1e9]">+{result.linked_monthly_benefit_krw.toLocaleString()}원</div>
                </div>
              </div>
            </div>
          </section>
          <section className="rounded-[24px] border border-slate-200/80 bg-white p-6">
            <div className="flex items-center gap-3">
              <span className="grid h-9 w-9 place-items-center rounded-xl bg-[#e6f8f5] text-[#159c8d]">
                <Target size={17} />
              </span>
              <div>
                <div className="text-[10px] font-extrabold uppercase tracking-[.18em] text-[#1eb8a6]">ALLOCATIONS</div>
                <h2 className="mt-1 text-[17px] font-extrabold tracking-[-.04em]">배분 내역</h2>
              </div>
            </div>
            <div className="mt-6 grid gap-3">
              {result.allocations.map((allocation, i) => (
                <div key={i} className="flex items-center justify-between rounded-xl bg-[#f7f9fc] px-4 py-3">
                  <span className="text-[12px] font-bold text-slate-600">{allocation.category}</span>
                  <span className="text-[13px] font-extrabold text-ink">{allocation.monthly_amount_krw.toLocaleString()}원</span>
                </div>
              ))}
            </div>
            {result.feasibility_warning && (
              <div className="mt-4 flex items-start gap-2 rounded-xl bg-[#fff0e7] p-3.5 text-[12px] font-bold text-[#c15f2c]">
                <TrendingUp size={15} className="mt-0.5 shrink-0" />
                {result.feasibility_warning}
              </div>
            )}
          </section>
        </div>
      )}

      <div className="mt-7 flex items-center gap-2 text-[11px] font-semibold text-slate-400">
        <CircleHelp size={14} /> 예상 혜택은 정책 조건에 따라 달라질 수 있어요.
      </div>
    </div>
  );
}

export default function SavingsPage() {
  const [activeTab, setActiveTab] = useState<SubTabKey>("plan");

  return (
    <DashboardLayout eyebrow="SAVINGS PLAN" title="저축플랜">
      <div className="mb-6 inline-flex gap-1.5 rounded-xl bg-[#eef3f9] p-1">
        {SUB_TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`rounded-lg px-4 py-2.5 text-[12px] font-extrabold transition ${
              activeTab === tab.key ? "bg-white text-[#2457d6] shadow-sm" : "text-slate-500"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "plan" && <SavingsPlanSection />}
      {activeTab === "subscriptions" && <SubscriptionsSection />}
      {activeTab === "cards" && <CardsSection />}
    </DashboardLayout>
  );
}
