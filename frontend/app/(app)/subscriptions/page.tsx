"use client";

import { useState } from "react";
import { callTool } from "@/lib/api";

type SubscriptionItem = {
  service_name: string;
  monthly_cost_krw: number;
};

type SubscriptionReportOutput = {
  month: string;
  items: SubscriptionItem[];
  total_cost_krw: number;
};

export default function SubscriptionsPage() {
  const [month, setMonth] = useState("2026-07");
  const [result, setResult] = useState<SubscriptionReportOutput | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    setLoading(true);
    const token = localStorage.getItem("token") ?? "";
    try {
      const output = await callTool<SubscriptionReportOutput>(token, "subscription_report", { month });
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
        <h1>📺 구독료 리포트</h1>
        <p>조회할 월을 입력하면 해당 월의 구독 서비스 사용 내역과 총 비용을 보여드립니다.</p>
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
            <span>{result.month} 총 구독료</span>
            <span className="amount">{result.total_cost_krw.toLocaleString()}원</span>
          </div>
          <div className="result-list">
            {result.items.map((item, i) => (
              <div key={i} className="result-item">
                <div className="result-item-title">{item.service_name}</div>
                <div className="result-item-row">
                  <span>월 비용</span>
                  <strong>{item.monthly_cost_krw.toLocaleString()}원</strong>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </>
  );
}
