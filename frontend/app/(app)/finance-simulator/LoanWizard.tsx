"use client";

// 정책연계 대출 시뮬레이터 (목업) — 상품 선택 → 조건 입력 → 예상 대출 가능액.
// 화면(스크린샷 2·3)을 그대로 옮긴 것으로, 모든 수치는 화면 설계용 예시값이다.

import { useState } from "react";
import { Landmark } from "lucide-react";
import {
  BackButton,
  MockDisclaimer,
  NextButton,
  PrelimRow,
  Segmented,
  SliderField,
  StepRail,
  WizardFrame,
  eok,
  manwon,
  type WizardStep,
} from "./wizardUi";

type LoanProduct = {
  id: string;
  name: string;
  desc: string;
  meta: string;
  capEok: number; // 상품 상한액 (억원)
  baseRate: number; // 수도권·신혼 기준 예시 금리
  ltv: number;
};

const PRODUCTS: LoanProduct[] = [
  {
    id: "dream",
    name: "청년주택드림 디딤돌대출",
    desc: "청년주택드림 청약통장 가입자 대상 주택 구입자금 대출, 최저 연 2.2%",
    meta: "만기 최대 40년 · 2026.08 기준",
    capEok: 4.0,
    baseRate: 0.034,
    ltv: 0.7,
  },
  {
    id: "didimdol",
    name: "내집마련 디딤돌대출",
    desc: "무주택 서민 주택 구입자금, 부부합산 6천만원 이하 · LTV 70%",
    meta: "만기 최대 30년 · 2026.08 기준",
    capEok: 2.5,
    baseRate: 0.038,
    ltv: 0.7,
  },
  {
    id: "newborn",
    name: "신생아 특례 디딤돌대출",
    desc: "2년 내 출산 가구 우대, 최저 연 1%대 · 소득상한 완화",
    meta: "만기 최대 30년 · 2026.08 기준",
    capEok: 4.0,
    baseRate: 0.028,
    ltv: 0.7,
  },
];

const STEPS: WizardStep[] = [
  { label: "상품 선택", sub: "대출상품 고르기" },
  { label: "정보 입력", sub: "내 조건 입력하기" },
  { label: "결과 확인", sub: "예상 대출 가능액" },
];

const DISCLAIMER =
  "본 결과는 화면 설계용 예시 수치이며 실제 심사 결과와 다를 수 있습니다. 정확한 한도·금리는 기금e든든 및 한국주택금융공사에서 다시 확인하세요.";

// 예시 계산.
function mockResult(
  p: LoanProduct,
  priceEok: number,
  married: boolean,
  region: "capital" | "local",
  firstHome: boolean,
) {
  const ltvAmountEok = Math.round(priceEok * p.ltv * 10) / 10;
  const maxEok = Math.min(ltvAmountEok, p.capEok);

  let rate = p.baseRate;
  if (region === "local") rate -= 0.002;
  if (firstHome) rate -= 0.002;
  if (!married) rate += 0.002;
  rate = Math.max(rate, 0.012);

  const principal = maxEok * 100_000_000;
  const months = 360;
  const mrate = rate / 12;
  // 원리금균등
  const factor = Math.pow(1 + mrate, months);
  const levelPayment = (principal * mrate * factor) / (factor - 1);
  const levelInterestTotal = levelPayment * months - principal;
  // 원금균등 (첫 달 상환액이 가장 큼)
  const firstPayment = principal / months + principal * mrate;
  const equalPrincipalInterestTotal = principal * mrate * (months + 1) / 2;

  return {
    ltvAmountEok,
    maxEok,
    rate,
    levelPaymentManwon: levelPayment / 10_000,
    levelInterestTotalManwon: levelInterestTotal / 10_000,
    firstPaymentManwon: firstPayment / 10_000,
    equalPrincipalInterestTotalManwon: equalPrincipalInterestTotal / 10_000,
  };
}

export default function LoanWizard() {
  const [step, setStep] = useState(0);
  const [productId, setProductId] = useState<string | null>(null);
  const [married, setMarried] = useState<"married" | "single">("married");
  const [income, setIncome] = useState(8500);
  const [priceEok10, setPriceEok10] = useState(52); // 0.1억 단위 (5.2억)
  const [region, setRegion] = useState<"capital" | "local">("capital");
  const [firstHome, setFirstHome] = useState<"first" | "none">("none");
  const [repayment, setRepayment] = useState<"level" | "equal">("level");

  const product = PRODUCTS.find((p) => p.id === productId) ?? null;
  const priceEok = priceEok10 / 10;

  return (
    <div className="grid gap-8 lg:grid-cols-[180px_1fr]">
      <div className="hidden lg:block">
        <StepRail steps={STEPS} current={step} />
      </div>

      {step === 0 && (
        <WizardFrame
          eyebrow="대출 시뮬레이터 · 1단계"
          title="어떤 정책 대출을 확인해볼까요"
          footer={
            <>
              <span />
              <NextButton label="다음" onClick={() => setStep(1)} disabled={!product} />
            </>
          }
        >
          <div className="grid gap-3">
            {PRODUCTS.map((p) => {
              const selected = p.id === productId;
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setProductId(p.id)}
                  className={`flex items-center justify-between gap-4 rounded-2xl border p-5 text-left transition ${
                    selected ? "border-[#b5623a] bg-[#fdf1ea]" : "border-slate-200 bg-white hover:border-slate-300"
                  }`}
                >
                  <div>
                    <div className="text-[14px] font-extrabold text-ink">{p.name}</div>
                    <p className="mt-1 text-[12px] leading-5 text-slate-500">{p.desc}</p>
                    <div className="mt-1.5 text-[11px] font-semibold text-slate-400">
                      {p.meta} · 상한 {eok(p.capEok)}
                    </div>
                  </div>
                  <span
                    className={`shrink-0 rounded-full border px-4 py-1.5 text-[12px] font-extrabold ${
                      selected ? "border-[#b5623a] text-[#b5623a]" : "border-slate-300 text-slate-400"
                    }`}
                  >
                    {selected ? "선택됨" : "선택"}
                  </span>
                </button>
              );
            })}
          </div>
        </WizardFrame>
      )}

      {step === 1 && product && (
        <WizardFrame
          eyebrow="대출 시뮬레이터 · 2단계"
          title="내 조건을 입력해주세요"
          footer={
            <>
              <BackButton onClick={() => setStep(0)} />
              <NextButton label="결과 보기" onClick={() => setStep(2)} />
            </>
          }
        >
          <div className="grid gap-6 sm:grid-cols-2">
            <div>
              <div className="mb-2 text-[12px] font-extrabold text-slate-700">혼인 여부</div>
              <Segmented
                options={[
                  { value: "married", label: "신혼부부(예정 포함)" },
                  { value: "single", label: "미혼" },
                ]}
                value={married}
                onChange={setMarried}
              />
            </div>
            <SliderField
              label="부부합산 연소득"
              valueLabel={manwon(income)}
              min={0}
              max={15000}
              step={100}
              value={income}
              onChange={setIncome}
            />
            <SliderField
              label="희망 주택가격"
              valueLabel={eok(priceEok)}
              min={10}
              max={90}
              step={1}
              value={priceEok10}
              onChange={setPriceEok10}
            />
            <div>
              <div className="mb-2 text-[12px] font-extrabold text-slate-700">지역</div>
              <Segmented
                options={[
                  { value: "capital", label: "수도권" },
                  { value: "local", label: "지방" },
                ]}
                value={region}
                onChange={setRegion}
              />
            </div>
            <div className="sm:col-span-2">
              <div className="mb-2 text-[12px] font-extrabold text-slate-700">생애최초 주택구입자 여부</div>
              <Segmented
                options={[
                  { value: "first", label: "생애최초" },
                  { value: "none", label: "해당 없음" },
                ]}
                value={firstHome}
                onChange={setFirstHome}
              />
            </div>
          </div>

          <div className="mt-7 rounded-2xl border border-slate-200 bg-[#f7f9fc] px-5 py-2">
            <div className="py-2 text-[11px] font-extrabold uppercase tracking-[.16em] text-slate-400">자격 예비판정</div>
            <PrelimRow label="소득 조건 (부부합산 1억원 이하)" ok={income <= 10000} />
            <PrelimRow label="주택가격 조건 (6억원 이하)" ok={priceEok <= 6} />
          </div>
        </WizardFrame>
      )}

      {step === 2 && product && (
        <WizardFrame
          eyebrow="대출 시뮬레이터 · 3단계"
          title="예상 대출 가능액"
          footer={
            <>
              <BackButton onClick={() => setStep(1)} />
              <NextButton
                label="다른 상품 보기"
                onClick={() => {
                  setStep(0);
                  setProductId(null);
                }}
              />
            </>
          }
        >
          {(() => {
            const r = mockResult(product, priceEok, married === "married", region, firstHome === "first");
            const payLabel = repayment === "level" ? r.levelPaymentManwon : r.firstPaymentManwon;
            const interestTotal =
              repayment === "level" ? r.levelInterestTotalManwon : r.equalPrincipalInterestTotalManwon;
            return (
              <div>
                <div className="rounded-2xl bg-[#faf3ee] p-6">
                  <div className="flex items-center gap-2 text-[11px] font-extrabold uppercase tracking-[.16em] text-[#b5623a]">
                    <Landmark size={13} /> {product.name}
                  </div>
                  <div className="mt-2 text-[11px] font-bold text-slate-400">최대 대출 가능액</div>
                  <div className="mt-1 text-[40px] font-extrabold tracking-[-.05em] text-[#9a3412]">{eok(r.maxEok)}</div>
                  <p className="mt-1 text-[12px] font-semibold text-slate-500">
                    LTV 적용액 {eok(r.ltvAmountEok)}과 상품 상한액 {eok(product.capEok)} 중 낮은 금액 기준
                  </p>
                </div>

                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <div className="rounded-2xl border border-slate-200 bg-white p-5">
                    <div className="text-[11px] font-bold text-slate-400">적용 금리</div>
                    <div className="mt-1.5 text-[20px] font-extrabold text-ink">연 {(r.rate * 100).toFixed(2)}%</div>
                    <div className="mt-1 text-[11px] font-semibold text-slate-400">
                      소득구간 + {region === "capital" ? "수도권" : "지방"} 기준
                    </div>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-white p-5">
                    <div className="text-[11px] font-bold text-slate-400">
                      {repayment === "level" ? "월 상환액 (30년, 원리금균등)" : "첫 달 상환액 (30년, 원금균등)"}
                    </div>
                    <div className="mt-1.5 text-[20px] font-extrabold text-ink">{manwon(payLabel)}</div>
                    <div className="mt-1 text-[11px] font-semibold text-slate-400">
                      총 이자비용 약 {manwon(interestTotal)}
                    </div>
                  </div>
                </div>

                <div className="mt-4 grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setRepayment("level")}
                    className={`h-11 rounded-xl border text-[12px] font-extrabold transition ${
                      repayment === "level"
                        ? "border-[#0d1b36] bg-white text-[#0d1b36]"
                        : "border-slate-200 bg-white text-slate-400"
                    }`}
                  >
                    원리금균등
                  </button>
                  <button
                    type="button"
                    onClick={() => setRepayment("equal")}
                    className={`h-11 rounded-xl border text-[12px] font-extrabold transition ${
                      repayment === "equal"
                        ? "border-[#0d1b36] bg-white text-[#0d1b36]"
                        : "border-slate-200 bg-white text-slate-400"
                    }`}
                  >
                    원금균등 (초기 상환액 더 큼)
                  </button>
                </div>

                <MockDisclaimer text={DISCLAIMER} />
              </div>
            );
          })()}
        </WizardFrame>
      )}
    </div>
  );
}
