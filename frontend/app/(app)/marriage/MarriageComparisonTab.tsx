"use client";

import { useEffect, useState } from "react";
import {
  AlertTriangle,
  Home,
  Info,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import {
  compareMarriageScenarios,
  getMe,
  type HousingLoanMarriageComparison,
  type MarriageComparisonOutput,
} from "@/lib/api";
import { krwToManwon, manwonToKrw } from "@/lib/profileOptions";

// 2026-09-03 재작업("혼인신고 계산기도 특정 정책 타겟팅해야 함" + "디자인도 정책
// 시뮬레이터처럼 동적으로", 사용자 요청): 정책 DB 전체 스캔 대신, 실제로 미혼용/
// 기혼용이 이름부터 따로 있는 고정 기준 2개(버팀목 전세자금대출/디딤돌대출)의 실제
// 조건 차이를 보여준다. 디자인은 정책금융 시뮬레이터(/finance-simulator)와 동일한
// 다크 히어로 카드 패턴을 재사용했다.
function HousingComparisonCard({
  comparison,
}: {
  comparison: HousingLoanMarriageComparison;
}) {
  const title =
    comparison.housing_type === "jeonse"
      ? "전세자금대출"
      : "구입자금대출(디딤돌)";
  const { unmarried, married } = comparison;
  const rateDeltaPct = (married.policy_rate - unmarried.policy_rate) * 100;
  const interestDelta =
    married.monthly_interest_krw - unmarried.monthly_interest_krw;

  return (
    <div className="grid gap-5 xl:grid-cols-[1.4fr_.8fr]">
      <section className="relative overflow-hidden rounded-[24px] bg-[#0d1b36] p-7 text-white sm:p-9">
        <div className="absolute inset-0 bg-[linear-gradient(100deg,#0d1b36_12%,rgba(13,27,54,.86)_54%,rgba(13,27,54,.35))]" />
        <div className="relative">
          <div className="flex items-center gap-2 text-[10px] font-extrabold uppercase tracking-[.2em] text-[#9cc5ff]">
            <Home size={13} /> {title}
          </div>
          <div className="mt-4 grid grid-cols-2 gap-4">
            <div>
              <div className="text-[10px] font-bold text-blue-100/60">
                미혼 · {unmarried.product_name}
              </div>
              <div className="mt-2 text-[28px] font-extrabold tracking-[-.04em] sm:text-[32px]">
                {unmarried.eligible
                  ? `연 ${(unmarried.policy_rate * 100).toFixed(2)}%`
                  : "대상 아님"}
              </div>
            </div>
            <div>
              <div className="text-[10px] font-bold text-[#9cc5ff]">
                기혼 · {married.product_name}
              </div>
              <div className="mt-2 text-[28px] font-extrabold tracking-[-.04em] text-[#9cc5ff] sm:text-[32px]">
                {married.eligible
                  ? `연 ${(married.policy_rate * 100).toFixed(2)}%`
                  : "대상 아님"}
              </div>
            </div>
          </div>
          <div className="mt-6 grid grid-cols-2 gap-3">
            <div className="rounded-xl bg-white/10 p-3.5">
              <div className="text-[10px] font-bold text-blue-100/60">
                대출 가능액 · 월 이자
              </div>
              <div className="mt-2 text-[14px] font-extrabold">
                {unmarried.eligible
                  ? `${unmarried.loan_amount_krw.toLocaleString()}원 · 월 ${unmarried.monthly_interest_krw.toLocaleString()}원`
                  : "-"}
              </div>
            </div>
            <div className="rounded-xl bg-white/10 p-3.5">
              <div className="text-[10px] font-bold text-blue-100/60">
                대출 가능액 · 월 이자
              </div>
              <div className="mt-2 text-[14px] font-extrabold">
                {married.eligible
                  ? `${married.loan_amount_krw.toLocaleString()}원 · 월 ${married.monthly_interest_krw.toLocaleString()}원`
                  : "-"}
              </div>
            </div>
          </div>
        </div>
      </section>
      <section className="rounded-[24px] border border-slate-200/80 bg-white p-6">
        <div className="flex items-center gap-3">
          <span
            className={`grid h-9 w-9 place-items-center rounded-xl ${interestDelta > 0 ? "bg-[#fdeeee] text-rose-500" : "bg-[#e6f8f5] text-[#159c8d]"}`}
          >
            {interestDelta > 0 ? (
              <TrendingUp size={17} />
            ) : (
              <TrendingDown size={17} />
            )}
          </span>
          <div>
            <div className="text-[10px] font-extrabold uppercase tracking-[.18em] text-slate-400">
              결혼하면 뭐가 달라지나
            </div>
            <h2 className="mt-1 text-[15px] font-extrabold tracking-[-.03em]">
              혼인 후 변화
            </h2>
          </div>
        </div>
        {unmarried.eligible && married.eligible ? (
          <>
            <div className="mt-5 rounded-xl bg-[#f7f9fc] px-4 py-3.5">
              <div className="text-[11px] font-bold text-slate-500">
                금리 변화
              </div>
              <div
                className={`mt-1 text-[18px] font-extrabold ${rateDeltaPct <= 0 ? "text-[#159c8d]" : "text-rose-500"}`}
              >
                {rateDeltaPct > 0 ? "+" : ""}
                {rateDeltaPct.toFixed(2)}%p
              </div>
            </div>
            <div className="mt-3 rounded-xl bg-[#f7f9fc] px-4 py-3.5">
              <div className="text-[11px] font-bold text-slate-500">
                월 이자 변화
              </div>
              <div
                className={`mt-1 text-[18px] font-extrabold ${interestDelta <= 0 ? "text-[#159c8d]" : "text-rose-500"}`}
              >
                {interestDelta > 0 ? "+" : ""}
                {interestDelta.toLocaleString()}원
              </div>
            </div>
          </>
        ) : (
          <p className="mt-4 text-[12px] leading-5 text-slate-500">
            {!unmarried.eligible && !married.eligible
              ? "지금 소득 기준으로는 미혼/기혼 둘 다 이 상품 대상이 아니에요."
              : !unmarried.eligible
                ? "미혼일 땐 소득 기준을 초과해 대상이 아니지만, 혼인신고 후 소득상한이 넓어지면 대상이 돼요."
                : "지금은 대상이지만, 혼인신고 후 가구소득이 합산되면 소득상한을 넘어 대상에서 빠질 수 있어요."}
          </p>
        )}
        <p className="mt-4 text-[11px] leading-5 text-slate-500">
          {married.eligible ? married.summary : unmarried.summary}
        </p>
      </section>
    </div>
  );
}

export default function MarriageComparisonTab() {
  const [age, setAge] = useState("29");
  const [income, setIncome] = useState("4000");
  const [spouseIncome, setSpouseIncome] = useState("");
  const [targetPrice, setTargetPrice] = useState("25000");
  const [selfCapital, setSelfCapital] = useState("5000");
  const [result, setResult] = useState<MarriageComparisonOutput | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("token") ?? "";
    getMe(token)
      .then((me) => {
        if (me.age != null) setAge(String(me.age));
        if (me.annual_income_krw != null)
          setIncome(String(krwToManwon(me.annual_income_krw)));
        if (me.spouse_annual_income_krw != null)
          setSpouseIncome(String(krwToManwon(me.spouse_annual_income_krw)));
      })
      .catch(() => {});
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    setLoading(true);
    const token = localStorage.getItem("token") ?? "";
    try {
      const output = await compareMarriageScenarios(token, {
        age: Number(age),
        annual_income_krw: manwonToKrw(Number(income)),
        spouse_annual_income_krw: spouseIncome
          ? manwonToKrw(Number(spouseIncome))
          : null,
        target_price_krw: manwonToKrw(Number(targetPrice) || 0),
        self_capital_krw: manwonToKrw(Number(selfCapital) || 0),
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
      <div className="mb-6 flex items-start gap-3 rounded-2xl border border-slate-200/80 bg-white p-4">
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[#eef3ff] text-[#2457d6]">
          <Info size={17} />
        </span>
        <div>
          <div className="text-[13px] font-extrabold text-ink">
            실제 정책 데이터 기준 비교입니다
          </div>
          <p className="mt-1 text-[12px] leading-5 text-slate-500">
            {/* 2026-09-03 재작업: 혼인 여부에 따라 조건이 실제로 달라지는 국가 주택금융
                상품 2가지(미혼용/기혼용이 이름부터 따로 있는 걸로 확인된 것)만 고정
                기준으로 비교한다 — CachedPolicy 전체를 스캔해 자격 변화를 찾던 예전
                방식은 걷어냈다(사용자 판단: 밋밋한 결과만 내서 빼도 된다). 지역은 이
                계산에 안 쓰여서(LTV/금리/소득상한이 전국 공통) 더 이상 입력받지
                않는다(사용자 지적: "지역이 지금 필요한가 모르겠다"). */}
            혼인 여부에 따라 조건이 실제로 달라지는 국가 주택금융 상품 2가지를
            고정 기준으로 비교해요.
            <br />
            전세는 <b>[미혼] 청년전용 버팀목 전세자금대출</b> vs{" "}
            <b>[기혼] 신혼부부전용 버팀목 전세자금대출</b>,
            <br />
            매매는 <b>[미혼] 내집마련 디딤돌대출</b> vs{" "}
            <b>[기혼] 신혼부부전용 디딤돌대출</b>로 금리·대출한도· 월 이자를
            나란히 보여드려요.
          </p>
        </div>
      </div>

      <div className="rounded-[22px] border border-slate-200/80 bg-white p-6">
        <form onSubmit={handleSubmit} className="grid gap-4 sm:grid-cols-2">
          <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
            나이
            <input
              type="number"
              value={age}
              onChange={(e) => setAge(e.target.value)}
              className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
            />
          </label>
          <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
            연소득 (만원)
            <input
              type="number"
              value={income}
              onChange={(e) => setIncome(e.target.value)}
              className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
            />
          </label>
          <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
            배우자(예정) 연소득 (만원, 선택)
            <input
              type="number"
              value={spouseIncome}
              onChange={(e) => setSpouseIncome(e.target.value)}
              placeholder="입력하면 혼인 후 가구소득 합산 기준으로 비교해요"
              className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
            />
          </label>
          <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
            목표 주택가격/전세보증금 (만원)
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
          <button
            type="submit"
            disabled={loading}
            className="h-12 rounded-xl bg-[#2457d6] text-[13px] font-extrabold text-white shadow-[0_10px_20px_rgba(36,87,214,.18)] transition hover:bg-[#1949c1] disabled:opacity-50 sm:col-span-2"
          >
            {loading ? "비교하는 중..." : "혼인신고 전후 비교하기"}
          </button>
        </form>
      </div>

      {error && (
        <p className="mt-4 text-[13px] font-bold text-rose-500">{error}</p>
      )}

      {result && (
        <div className="mt-6 grid gap-6">
          <div className="flex items-start gap-2 rounded-xl bg-[#fff7e6] p-3.5 text-[12px] font-bold leading-5 text-[#946200]">
            <AlertTriangle size={15} className="mt-0.5 shrink-0" />
            금리·소득상한·대출한도는 2026년 8월 고시 기준 실제 수치예요.
            생애최초 우대, 지방 주택 인하 등 일부 조건은 반영하지 못했어요 —
            정확한 조건은 주택도시기금 공고를 확인하세요.
          </div>
          {result.housing_loan_comparisons.map((c) => (
            <HousingComparisonCard key={c.housing_type} comparison={c} />
          ))}
        </div>
      )}
    </div>
  );
}
