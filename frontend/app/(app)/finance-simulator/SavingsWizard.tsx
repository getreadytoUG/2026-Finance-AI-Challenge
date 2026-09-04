"use client";

// 정책연계 저축계좌상품 시뮬레이터 — 정보 입력 → 예상 만기수령액.
// 2026-09-03 재작업: 원래는 화면 설계용 목업(가짜 mockResult())이었는데, 실제
// 백엔드(savings_simulator/simulate_youth_future_savings)에 연결했다 — /savings
// 탭(YouthFutureSavingsSimulator)에 있던 것과 같은 실제 계산이다. 청년미래적금
// 하나만 실제로 지원해서(청년도약계좌는 신규가입 종료, 청년주택드림청약통장은
// 이 앱에 계산 로직이 없음) "상품 선택" 단계는 없앴다 — 없는 선택지를 있는 척
// 보여주지 않는다.

import { useEffect, useState } from "react";
import { PiggyBank, TrendingUp } from "lucide-react";
import { getMe, simulateYouthFutureSavings, type YouthFutureSavingsOutput } from "@/lib/api";
import { krwToManwon, manwonToKrw } from "@/lib/profileOptions";
import { formatApplicationPeriod } from "@/lib/policyFormat";
import NoteTooltip from "@/components/NoteTooltip";
import PolicyDetailLink from "@/components/PolicyDetailLink";
import { BackButton, DisclaimerNote, NextButton, SliderField, StepRail, WizardFrame, manwon, type WizardStep } from "./wizardUi";

const YOUTH_LEAP_ACCOUNT_STATUS_NOTE =
  "청년도약계좌는 2025년 12월 31일자로 신규가입이 종료됐어요(기존 가입자는 만기까지 그대로 유지). " +
  "2026년 6월부터는 후속 상품인 청년미래적금이 정부기여금·비과세 혜택을 이어받았고, 이 시뮬레이터는 청년미래적금 기준으로 계산해요.";

const STEPS: WizardStep[] = [
  { label: "정보 입력", sub: "내 조건 입력하기" },
  { label: "결과 확인", sub: "예상 만기수령액" },
];

const DISCLAIMER =
  "매칭비율·소득구간은 2026년 6월 출시 공고 기준 실제 수치예요. 다만 가구 중위소득 조건은 반영하지 못했고, " +
  "시중적금 비교 금리는 은행마다 달라 가정치예요 — 정확한 조건은 서민금융진흥원 공고를 확인하세요.";

export default function SavingsWizard() {
  const [step, setStep] = useState(0);
  const [monthly, setMonthly] = useState(50); // 만원 — 청년미래적금 월 납입 한도
  const [income, setIncome] = useState(3500); // 만원
  const [seedMoney, setSeedMoney] = useState(0); // 만원
  const [result, setResult] = useState<YouthFutureSavingsOutput | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("token") ?? "";
    getMe(token)
      .then((me) => {
        if (me.annual_income_krw != null) setIncome(krwToManwon(me.annual_income_krw));
        if (me.monthly_savings_capacity_krw != null) setMonthly(Math.min(50, krwToManwon(me.monthly_savings_capacity_krw)));
      })
      .catch(() => {});
  }, []);

  async function handleSubmit() {
    setError(null);
    setLoading(true);
    try {
      const token = localStorage.getItem("token") ?? "";
      const output = await simulateYouthFutureSavings(token, {
        monthly_amount_krw: manwonToKrw(monthly),
        annual_income_krw: manwonToKrw(income),
        seed_money_krw: manwonToKrw(seedMoney),
      });
      setResult(output);
      setStep(1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "계산에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[180px_1fr]">
      <div className="hidden lg:block">
        <StepRail steps={STEPS} current={step} />
      </div>

      {step === 0 && (
        <WizardFrame
          eyebrow="저축 시뮬레이터"
          title="내 조건을 입력해주세요"
          footer={
            <>
              <span className="flex items-center gap-2 text-[11px] font-extrabold uppercase tracking-[.16em] text-[#2457d6]">
                <PiggyBank size={13} /> 청년미래적금 기준
                <NoteTooltip text={YOUTH_LEAP_ACCOUNT_STATUS_NOTE} triggerClassName="text-[#2457d6]/60 hover:text-[#2457d6]" bubbleClassName="bg-[#0d1b36] text-white" />
              </span>
              <NextButton label={loading ? "계산 중..." : "결과 보기"} onClick={handleSubmit} disabled={loading} />
            </>
          }
        >
          <div className="grid gap-6 sm:grid-cols-2">
            <SliderField label="월 납입액" valueLabel={manwon(monthly)} min={10} max={50} step={5} value={monthly} onChange={setMonthly} />
            <SliderField label="본인 연소득" valueLabel={manwon(income)} min={0} max={9000} step={100} value={income} onChange={setIncome} />
            <SliderField label="시드머니 (기존 보유액)" valueLabel={manwon(seedMoney)} min={0} max={5000} step={100} value={seedMoney} onChange={setSeedMoney} />
            <div>
              <div className="mb-2 text-[12px] font-extrabold text-slate-700">가입 기간</div>
              <div className="flex h-12 items-center rounded-xl bg-[#eef3f9] px-4 text-[13px] font-extrabold text-slate-500">3년 (고정)</div>
            </div>
          </div>
          {error && <p className="mt-4 text-[13px] font-bold text-rose-500">{error}</p>}
        </WizardFrame>
      )}

      {step === 1 && result && (
        <WizardFrame
          eyebrow="저축 시뮬레이터"
          title="예상 만기수령액"
          footer={
            <>
              <BackButton onClick={() => setStep(0)} />
              <span />
            </>
          }
        >
          <div className="rounded-2xl bg-[#0d1b36] p-6 text-white sm:p-7">
            <div className="flex items-center gap-2 text-[10px] font-extrabold uppercase tracking-[.18em] text-[#9cc5ff]">
              <PiggyBank size={13} /> 청년미래적금
            </div>
            <h3 className="mt-3 text-[24px] font-extrabold tracking-[-.05em] sm:text-[28px]">
              {result.eligible ? (
                <>
                  만기에 <span className="text-[#9cc5ff]">{manwon(krwToManwon(result.policy_total_krw))}</span>을 받을 수 있어요.
                </>
              ) : (
                "이 상품은 지금 조건으로는 가입할 수 없어요."
              )}
            </h3>
            <p className="mt-3 text-[12px] leading-6 text-blue-100/70">{result.eligibility_note}</p>
            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl bg-white/10 p-3.5">
                <div className="text-[10px] font-bold text-blue-100/60">청년미래적금 만기수령액</div>
                <div className="mt-2 text-[15px] font-extrabold">{result.policy_total_krw.toLocaleString()}원</div>
              </div>
              <div className="rounded-xl bg-white/10 p-3.5">
                <div className="text-[10px] font-bold text-blue-100/60">일반 시중적금(가정 금리 기준)</div>
                <div className="mt-2 text-[15px] font-extrabold">{result.market_total_krw.toLocaleString()}원</div>
              </div>
            </div>
          </div>

          <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-5">
            <div className="flex items-center gap-3">
              <span className="grid h-9 w-9 place-items-center rounded-xl bg-[#e6f8f5] text-[#159c8d]">
                <TrendingUp size={17} />
              </span>
              <div>
                <div className="text-[10px] font-extrabold uppercase tracking-[.18em] text-[#1eb8a6]">핵심 가치</div>
                <div className="text-[14px] font-extrabold tracking-[-.03em] text-ink">추가 수익</div>
              </div>
            </div>
            <div className="mt-4 rounded-xl bg-[#f7f9fc] px-4 py-3.5">
              <div className="text-[11px] font-bold text-slate-500">일반 적금 대비 차액</div>
              <div className={`mt-1 text-[18px] font-extrabold ${result.benefit_diff_krw > 0 ? "text-[#159c8d]" : "text-slate-500"}`}>
                {result.benefit_diff_krw > 0 ? "+" : ""}
                {result.benefit_diff_krw.toLocaleString()}원
              </div>
            </div>
            <p className="mt-3 text-[12px] leading-5 text-slate-500">{result.summary}</p>
          </div>

          {result.matched_policies.length > 0 && (
            <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-5">
              <div className="text-[10px] font-extrabold uppercase tracking-[.18em] text-[#2457d6]">실제 정책 매칭</div>
              <div className="mt-1 text-[14px] font-extrabold tracking-[-.03em] text-ink">지금 내 조건으로 신청 가능한 저축 정책</div>
              <div className="mt-4 grid gap-3">
                {result.matched_policies.map((p) => (
                  <div key={p.policy_key} className="rounded-xl border border-slate-200/80 bg-[#f7f9fc] p-4">
                    <div className="text-[13px] font-extrabold text-ink">{p.policy_name}</div>
                    <p className="mt-1.5 text-[12px] leading-5 text-slate-500">{p.benefit_description}</p>
                    <div className="mt-1.5 text-[11px] font-semibold text-slate-400">신청 기간 {formatApplicationPeriod(p.application_period)}</div>
                    <PolicyDetailLink url={p.reference_url} className="mt-1.5" />
                  </div>
                ))}
              </div>
            </div>
          )}

          <DisclaimerNote text={DISCLAIMER} />
        </WizardFrame>
      )}
    </div>
  );
}
