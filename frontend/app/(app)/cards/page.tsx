"use client";

import { useState } from "react";
import { callTool } from "@/lib/api";

type CategorySpending = {
  category: string;
  amount_krw: number;
};

type CardSpendingReportOutput = {
  month: string;
  categories: CategorySpending[];
  total_amount_krw: number;
};

export default function CardsPage() {
  const [month, setMonth] = useState("2026-07");
  const [result, setResult] = useState<CardSpendingReportOutput | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    setLoading(true);
    const token = localStorage.getItem("token") ?? "";
    try {
      const output = await callTool<CardSpendingReportOutput>(token, "card_spending_report", { month });
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
        <h1>💳 카드소비 리포트</h1>
        <p>조회할 월을 입력하면 해당 월의 카드 사용 내역을 카테고리별로 보여드립니다.</p>
      </div>

      <div className="card">
        <form onSubmit={handleSubmit}>
          <label className="field">
            <span className="field-label">조회 월 (YYYY-MM)</span>
            <input className="input" type="text" value={month} onChange={(e) => setMonth(e.target.value)} />
          </label>
          <button className="btn" type="submit" disabled={loading}>
            {loading ? "조회 중..." : "리포트 보기"}
          </button>
        </form>
      </div>

      {error && <p className="error-text" style={{ marginTop: 16 }}>{error}</p>}

      {result && (
        <>
          <div className="summary-banner">
            <span>{result.month} 총 카드 사용액</span>
            <span className="amount">{result.total_amount_krw.toLocaleString()}원</span>
          </div>
          <div className="result-list">
            {result.categories.map((category, i) => (
              <div key={i} className="result-item">
                <div className="result-item-title">{category.category}</div>
                <div className="result-item-row">
                  <span>사용액</span>
                  <strong>{category.amount_krw.toLocaleString()}원</strong>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </>
  );
}
