"use client";

import { useState } from "react";
import { callTool } from "@/lib/api";

type SavingsAllocation = {
  category: string;
  monthly_amount_krw: number;
};

type SavingsPlanOutput = {
  allocations: SavingsAllocation[];
  monthly_required_krw: number;
};

export default function SavingsPage() {
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
      <div className="page-header">
        <h1>💰 저축플랜</h1>
        <p>월급과 목표 금액을 입력하면 매달 얼마씩 저축해야 하는지 배분해드립니다.</p>
      </div>

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
