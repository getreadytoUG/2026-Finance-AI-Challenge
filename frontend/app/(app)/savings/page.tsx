"use client";

import { useState } from "react";
import { callTool } from "@/lib/api";
import SubscriptionsSection from "./SubscriptionsSection";
import CardsSection from "./CardsSection";

type SavingsAllocation = {
  category: string;
  monthly_amount_krw: number;
};

type SavingsPlanOutput = {
  allocations: SavingsAllocation[];
  monthly_required_krw: number;
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
    <>
      <div className="card">
        <form onSubmit={handleSubmit}>
          <label className="field">
            <span className="field-label">월급 (원)</span>
            <input className="input" type="number" value={monthlyIncome} onChange={(e) => setMonthlyIncome(e.target.value)} />
          </label>
          <label className="field">
            <span className="field-label">목표 금액 (원)</span>
            <input className="input" type="number" value={goalAmount} onChange={(e) => setGoalAmount(e.target.value)} />
          </label>
          <label className="field">
            <span className="field-label">목표 기간 (개월)</span>
            <input className="input" type="number" value={goalMonths} onChange={(e) => setGoalMonths(e.target.value)} />
          </label>
          <button className="btn" type="submit" disabled={loading}>
            {loading ? "계산 중..." : "저축 플랜 만들기"}
          </button>
        </form>
      </div>

      {error && <p className="error-text" style={{ marginTop: 16 }}>{error}</p>}

      {result && (
        <>
          <div className="summary-banner">
            <span>월 저축 필요액</span>
            <span className="amount">{result.monthly_required_krw.toLocaleString()}원</span>
          </div>
          <div className="result-list">
            {result.allocations.map((allocation, i) => (
              <div key={i} className="result-item">
                <div className="result-item-title">{allocation.category}</div>
                <div className="result-item-row">
                  <span>월 배분액</span>
                  <strong>{allocation.monthly_amount_krw.toLocaleString()}원</strong>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </>
  );
}

export default function SavingsPage() {
  const [activeTab, setActiveTab] = useState<SubTabKey>("plan");

  return (
    <>
      <div className="page-header">
        <h1>💰 저축플랜</h1>
        <p>월급과 목표 금액으로 저축 계획을 세우고, 구독료·카드소비 리포트로 절약 여지를 함께 확인하세요.</p>
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
        {SUB_TABS.map((tab) => (
          <button
            key={tab.key}
            className="btn-ghost"
            onClick={() => setActiveTab(tab.key)}
            style={{
              borderRadius: 999,
              background: activeTab === tab.key ? "var(--primary-tint)" : undefined,
              color: activeTab === tab.key ? "var(--primary)" : undefined,
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "plan" && <SavingsPlanSection />}
      {activeTab === "subscriptions" && <SubscriptionsSection />}
      {activeTab === "cards" && <CardsSection />}
    </>
  );
}
