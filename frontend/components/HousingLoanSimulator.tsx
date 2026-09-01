"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Home, TrendingDown } from "lucide-react";
import { getMe, simulateHousingLoan, type HousingLoanOutput } from "@/lib/api";
import { krwToManwon, manwonToKrw } from "@/lib/profileOptions";

const HOUSING_TYPE_OPTIONS = [
  { value: "jeonse" as const, label: "전세" },
  { value: "purchase" as const, label: "매매" },
];

export default function HousingLoanSimulator() {
  const [housingType, setHousingType] = useState<"jeonse" | "purchase">("jeonse");
  const [targetPrice, setTargetPrice] = useState("25000");
  const [selfCapital, setSelfCapital] = useState("5000");
  const [householdIncome, setHouseholdIncome] = useState("");
  const [result, setResult] = useState<HousingLoanOutput | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("token") ?? "";
    getMe(token)
      .then((me) => {
        const household = (me.annual_income_krw ?? 0) + (me.spouse_annual_income_krw ?? 0);
        if (household > 0) setHouseholdIncome(String(krwToManwon(household)));
      })
      .catch(() => {});
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    setLoading(true);
    try {
      const token = localStorage.getItem("token") ?? "";
      const output = await simulateHousingLoan(token, {
        housing_type: housingType,
        target_price_krw: manwonToKrw(Number(targetPrice)),
        self_capital_krw: manwonToKrw(Number(selfCapital)),
        household_annual_income_krw: manwonToKrw(Number(householdIncome)),
      });
      setResult(output);
    } catch (err) {
      setError(err instanceof Error ? err.message : "계산에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="rounded-[22px] border border-slate-200/80 bg-white p-6">
        <form onSubmit={handleSubmit} className="grid gap-4 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <div className="mb-2 text-[12px] font-extrabold text-slate-700">희망 주거 형태</div>
            <div className="flex gap-2">
              {HOUSING_TYPE_OPTIONS.map((o) => (
                <button
                  key={o.value}
                  type="button"
                  onClick={() => setHousingType(o.value)}
                  className={`h-12 flex-1 rounded-xl text-[13px] font-extrabold transition ${
                    housingType === o.value ? "bg-[#2457d6] text-white" : "bg-[#eef3f9] text-slate-500 hover:bg-[#e3eaf6]"
                  }`}
                >
                  {o.label}
                </button>
              ))}
            </div>
          </div>
          <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
            목표 {housingType === "jeonse" ? "보증금" : "주택 가격"} (만원)
            <input
              type="number"
              min={0}
              value={targetPrice}
              onChange={(e) => setTargetPrice(e.target.value)}
              className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
            />
          </label>
          <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
            보유 자기자본 (만원)
            <input
              type="number"
              min={0}
              value={selfCapital}
              onChange={(e) => setSelfCapital(e.target.value)}
              className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
            />
          </label>
          <label className="grid gap-2 text-[12px] font-extrabold text-slate-700 sm:col-span-2">
            부부 합산 연소득 (만원)
            <input
              type="number"
              min={0}
              value={householdIncome}
              onChange={(e) => setHouseholdIncome(e.target.value)}
              className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
            />
          </label>
          <button
            type="submit"
            disabled={loading || !targetPrice || !selfCapital || !householdIncome}
            className="h-12 rounded-xl bg-[#2457d6] text-[13px] font-extrabold text-white shadow-[0_10px_20px_rgba(36,87,214,.18)] transition hover:bg-[#1949c1] disabled:opacity-50 sm:col-span-2"
          >
            {loading ? "계산 중..." : "시뮬레이션 하기"}
          </button>
        </form>
      </div>

      {error && <p className="mt-4 text-[13px] font-bold text-rose-500">{error}</p>}

      {result && (
        <div className="mt-6">
          <div className="mb-4 flex items-start gap-2 rounded-xl bg-[#fff7e6] p-3.5 text-[12px] font-bold leading-5 text-[#946200]">
            <AlertTriangle size={15} className="mt-0.5 shrink-0" />
            아래 LTV·금리는 실제 정부 고시가 아니라 예시 수치예요. 정확한 조건은 주택도시기금 공고를 확인하세요.
          </div>

          <div className="grid gap-5 xl:grid-cols-[1.4fr_.8fr]">
            <section className="relative overflow-hidden rounded-[24px] bg-[#0d1b36] p-7 text-white sm:p-9">
              <div className="absolute inset-0 bg-[linear-gradient(100deg,#0d1b36_12%,rgba(13,27,54,.86)_54%,rgba(13,27,54,.35))]" />
              <div className="relative">
                <div className="flex items-center gap-2 text-[10px] font-extrabold uppercase tracking-[.2em] text-[#9cc5ff]">
                  <Home size={13} /> {result.product_name.toUpperCase()}
                </div>
                <h2 className="mt-3 text-[24px] font-extrabold tracking-[-.05em] sm:text-[28px]">{result.summary}</h2>
                <div className="mt-8 grid max-w-[480px] grid-cols-2 gap-3">
                  <div className="rounded-xl bg-white/10 p-3.5">
                    <div className="text-[10px] font-bold text-blue-100/60">정책 대출 가능액 (LTV {(result.ltv_rate * 100).toFixed(0)}%)</div>
                    <div className="mt-2 text-[16px] font-extrabold">{result.loan_amount_krw.toLocaleString()}원</div>
                  </div>
                  <div className="rounded-xl bg-white/10 p-3.5">
                    <div className="text-[10px] font-bold text-blue-100/60">정책 금리 연 {(result.policy_rate * 100).toFixed(1)}%</div>
                    <div className="mt-2 text-[16px] font-extrabold">월 {result.monthly_interest_krw.toLocaleString()}원</div>
                  </div>
                </div>
              </div>
            </section>
            <section className="rounded-[24px] border border-slate-200/80 bg-white p-6">
              <div className="flex items-center gap-3">
                <span className="grid h-9 w-9 place-items-center rounded-xl bg-[#e6f8f5] text-[#159c8d]">
                  <TrendingDown size={17} />
                </span>
                <div>
                  <div className="text-[10px] font-extrabold uppercase tracking-[.18em] text-[#1eb8a6]">SAVINGS</div>
                  <h2 className="mt-1 text-[15px] font-extrabold tracking-[-.03em]">시중 대비 절감 (예시)</h2>
                </div>
              </div>
              <div className="mt-5 grid gap-3">
                <div className="rounded-xl bg-[#f7f9fc] px-4 py-3.5">
                  <div className="text-[11px] font-bold text-slate-500">시중 상품 월 이자 (연 {(result.market_rate * 100).toFixed(1)}%)</div>
                  <div className="mt-1 text-[15px] font-extrabold text-ink">{result.market_monthly_interest_krw.toLocaleString()}원</div>
                </div>
                <div className="rounded-xl bg-[#e6f8f5] px-4 py-3.5">
                  <div className="text-[11px] font-bold text-[#159c8d]">월 이자 절감액</div>
                  <div className="mt-1 text-[18px] font-extrabold text-[#159c8d]">{result.monthly_saving_krw.toLocaleString()}원</div>
                </div>
              </div>
            </section>
          </div>
        </div>
      )}
    </div>
  );
}
