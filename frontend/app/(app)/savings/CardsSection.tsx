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

export default function CardsSection() {
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
    <div>
      <div className="rounded-[22px] border border-slate-200/80 bg-white p-6">
        <form onSubmit={handleSubmit} className="grid gap-4 sm:grid-cols-[1fr_auto] sm:items-end">
          <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
            조회 월 (YYYY-MM)
            <input
              type="text"
              value={month}
              onChange={(e) => setMonth(e.target.value)}
              className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
            />
          </label>
          <button
            type="submit"
            disabled={loading}
            className="h-12 rounded-xl bg-[#2457d6] px-6 text-[13px] font-extrabold text-white shadow-[0_10px_20px_rgba(36,87,214,.18)] transition hover:bg-[#1949c1] disabled:opacity-50"
          >
            {loading ? "조회 중..." : "리포트 보기"}
          </button>
        </form>
      </div>

      {error && <p className="mt-4 text-[13px] font-bold text-rose-500">{error}</p>}

      {result && (
        <>
          <div className="mt-6 flex items-center justify-between rounded-2xl bg-[#eef3ff] px-5 py-4 font-extrabold text-[#2457d6]">
            <span>{result.month} 총 카드 사용액</span>
            <span className="text-[18px]">{result.total_amount_krw.toLocaleString()}원</span>
          </div>
          <div className="mt-4 grid gap-3">
            {result.categories.map((category, i) => (
              <div key={i} className="rounded-2xl border border-slate-200/80 bg-white p-4">
                <div className="text-[14px] font-extrabold text-ink">{category.category}</div>
                <div className="mt-1 flex items-center justify-between text-[12px] text-slate-500">
                  <span>사용액</span>
                  <strong className="text-ink">{category.amount_krw.toLocaleString()}원</strong>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
