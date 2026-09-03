"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, ListChecks, PiggyBank, TrendingUp } from "lucide-react";
import { getMe, simulateYouthFutureSavings, type YouthFutureSavingsOutput } from "@/lib/api";
import { krwToManwon, manwonToKrw } from "@/lib/profileOptions";
import NoteTooltip from "@/components/NoteTooltip";
import PolicyDetailLink from "@/components/PolicyDetailLink";

// 2026-09-03: 청년도약계좌 신규가입 종료(2025-12-31) 이후 후속 상품인
// 청년미래적금 기준으로 전면 재작업했다. 이 안내는 그 배경을 모르는 사용자에게
// "왜 도약계좌가 아니라 미래적금이 나오지?"를 설명한다(사용자 요청, AiSearchResultsPanel의
// 데이터 정합성 안내 아이콘과 동일한 hover 패턴 재사용).
const YOUTH_LEAP_ACCOUNT_STATUS_NOTE =
  "청년도약계좌는 2025년 12월 31일자로 신규가입이 종료됐어요(기존 가입자는 만기까지 그대로 유지). " +
  "2026년 6월부터는 후속 상품인 청년미래적금이 정부기여금·비과세 혜택을 이어받았고, 이 시뮬레이터는 청년미래적금 기준으로 계산해요.";

export default function YouthFutureSavingsSimulator() {
  const [monthlyAmount, setMonthlyAmount] = useState("50"); // 청년미래적금 월 납입 한도(50만원) 기본값, 프로필 로드 후 덮어씀
  const [annualIncome, setAnnualIncome] = useState("");
  const [seedMoney, setSeedMoney] = useState("0");
  const [result, setResult] = useState<YouthFutureSavingsOutput | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("token") ?? "";
    getMe(token)
      .then((me) => {
        if (me.annual_income_krw != null) setAnnualIncome(String(krwToManwon(me.annual_income_krw)));
        if (me.monthly_savings_capacity_krw != null) setMonthlyAmount(String(krwToManwon(me.monthly_savings_capacity_krw)));
        else setMonthlyAmount("50"); // 청년미래적금 월 납입 한도(50만원)에 맞춘 기본값
      })
      .catch(() => setMonthlyAmount("50"));
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    setLoading(true);
    try {
      const token = localStorage.getItem("token") ?? "";
      const output = await simulateYouthFutureSavings(token, {
        monthly_amount_krw: manwonToKrw(Number(monthlyAmount)),
        annual_income_krw: manwonToKrw(Number(annualIncome)),
        seed_money_krw: manwonToKrw(Number(seedMoney) || 0),
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
        <div className="mb-4 flex items-center gap-2 text-[11px] font-extrabold uppercase tracking-[.18em] text-[#2457d6]">
          <PiggyBank size={13} /> 청년미래적금 기준
          <NoteTooltip
            text={YOUTH_LEAP_ACCOUNT_STATUS_NOTE}
            triggerClassName="text-[#2457d6]/60 hover:text-[#2457d6]"
            bubbleClassName="bg-[#0d1b36] text-white"
          />
        </div>
        <form onSubmit={handleSubmit} className="grid gap-4 sm:grid-cols-2">
          <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
            월 저축 가능 금액 (만원)
            <input
              type="number"
              min={0}
              value={monthlyAmount}
              onChange={(e) => setMonthlyAmount(e.target.value)}
              className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
            />
          </label>
          <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
            본인 연소득 (만원)
            <input
              type="number"
              min={0}
              value={annualIncome}
              onChange={(e) => setAnnualIncome(e.target.value)}
              className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
            />
          </label>
          <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
            시드머니 (기존 보유액, 만원, 선택)
            <input
              type="number"
              min={0}
              value={seedMoney}
              onChange={(e) => setSeedMoney(e.target.value)}
              className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
            />
          </label>
          <div className="grid gap-2 text-[12px] font-extrabold text-slate-700">
            가입 기간
            <div className="flex h-12 items-center rounded-xl bg-[#eef3f9] px-4 text-[13px] font-extrabold text-slate-500">
              3년 (고정)
            </div>
          </div>
          <button
            type="submit"
            disabled={loading || !monthlyAmount || !annualIncome}
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
            매칭비율·소득구간은 2026년 6월 출시 공고 기준 실제 수치예요. 다만 가구 중위소득 조건은 반영하지
            못했고, 시중적금 비교 금리는 은행마다 달라 가정치예요 — 정확한 조건은 서민금융진흥원 공고를
            확인하세요.
          </div>

          <div className="grid gap-5 xl:grid-cols-[1.4fr_.8fr]">
            <section className="relative overflow-hidden rounded-[24px] bg-[#0d1b36] p-7 text-white sm:p-9">
              <div className="absolute inset-0 bg-[linear-gradient(100deg,#0d1b36_12%,rgba(13,27,54,.86)_54%,rgba(13,27,54,.35))]" />
              <div className="relative">
                <div className="flex items-center gap-2 text-[10px] font-extrabold uppercase tracking-[.2em] text-[#9cc5ff]">
                  <PiggyBank size={13} /> 청년미래적금
                  <NoteTooltip
                    text={YOUTH_LEAP_ACCOUNT_STATUS_NOTE}
                    triggerClassName="text-[#9cc5ff]/70 hover:text-[#9cc5ff]"
                    bubbleClassName="bg-white text-[#0d1b36] ring-1 ring-black/5"
                  />
                </div>
                <h2 className="mt-3 text-[26px] font-extrabold tracking-[-.06em] sm:text-[32px]">
                  {result.eligible ? (
                    <>
                      만기에 <span className="text-[#9cc5ff]">{result.policy_total_krw.toLocaleString()}원</span>을 받을 수 있어요.
                    </>
                  ) : (
                    "이 상품은 지금 조건으로는 가입할 수 없어요."
                  )}
                </h2>
                <p className="mt-4 text-[12px] leading-6 text-blue-100/70">{result.eligibility_note}</p>
                <div className="mt-8 grid max-w-[480px] grid-cols-2 gap-3">
                  <div className="rounded-xl bg-white/10 p-3.5">
                    <div className="text-[10px] font-bold text-blue-100/60">청년미래적금 만기수령액</div>
                    <div className="mt-2 text-[16px] font-extrabold">{result.policy_total_krw.toLocaleString()}원</div>
                  </div>
                  <div className="rounded-xl bg-white/10 p-3.5">
                    <div className="text-[10px] font-bold text-blue-100/60">일반 시중적금(가정 금리 기준)</div>
                    <div className="mt-2 text-[16px] font-extrabold">{result.market_total_krw.toLocaleString()}원</div>
                  </div>
                </div>
              </div>
            </section>
            <section className="rounded-[24px] border border-slate-200/80 bg-white p-6">
              <div className="flex items-center gap-3">
                <span className="grid h-9 w-9 place-items-center rounded-xl bg-[#e6f8f5] text-[#159c8d]">
                  <TrendingUp size={17} />
                </span>
                <div>
                  <div className="text-[10px] font-extrabold uppercase tracking-[.18em] text-[#1eb8a6]">핵심 가치</div>
                  <h2 className="mt-1 text-[15px] font-extrabold tracking-[-.03em]">추가 수익</h2>
                </div>
              </div>
              <div className="mt-5 rounded-xl bg-[#f7f9fc] px-4 py-3.5">
                <div className="text-[11px] font-bold text-slate-500">일반 적금 대비 차액</div>
                <div className={`mt-1 text-[18px] font-extrabold ${result.benefit_diff_krw > 0 ? "text-[#159c8d]" : "text-slate-500"}`}>
                  {result.benefit_diff_krw > 0 ? "+" : ""}
                  {result.benefit_diff_krw.toLocaleString()}원
                </div>
              </div>
              <p className="mt-4 text-[12px] leading-5 text-slate-500">{result.summary}</p>
            </section>
          </div>

          {/* 위 계산은 청년미래적금 하나만 다루지만, 이 목록은 실제 DB 정책에서 지금 내
              조건(나이/소득/지역 등, 저장된 프로필 기준)으로 진짜 자격되는 것만 골라온다
              (2026-09-02 추가) — "이 상품 계산" vs "그 외 실제 신청 가능한 정책"을
              명확히 구분해서 보여준다. */}
          <section className="mt-5 rounded-[24px] border border-slate-200/80 bg-white p-6">
            <div className="flex items-center gap-3">
              <span className="grid h-9 w-9 place-items-center rounded-xl bg-[#eef3ff] text-[#2457d6]">
                <ListChecks size={17} />
              </span>
              <div>
                <div className="text-[10px] font-extrabold uppercase tracking-[.18em] text-[#2457d6]">실제 정책 매칭</div>
                <h2 className="mt-1 text-[15px] font-extrabold tracking-[-.03em]">지금 내 조건으로 신청 가능한 저축 정책</h2>
              </div>
            </div>
            {result.matched_policies.length === 0 ? (
              <p className="mt-4 text-[13px] font-bold text-slate-400">지금 조건에 맞는 저축/자산형성 정책을 DB에서 찾지 못했어요.</p>
            ) : (
              <div className="mt-4 grid gap-3">
                {result.matched_policies.map((p) => (
                  <div key={p.policy_key} className="rounded-xl border border-slate-200/80 bg-[#f7f9fc] p-4">
                    <div className="text-[13px] font-extrabold text-ink">{p.policy_name}</div>
                    <p className="mt-1.5 text-[12px] leading-5 text-slate-500">{p.benefit_description}</p>
                    <div className="mt-1.5 text-[11px] font-semibold text-slate-400">신청 기간 {p.application_period}</div>
                    <PolicyDetailLink url={p.reference_url} className="mt-1.5" />
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
