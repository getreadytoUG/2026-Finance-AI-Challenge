"use client";

// 정책연계 대출 시뮬레이터 — 상품(전세/매매) 선택 → 정보 입력 → 예상 대출 가능액.
// 2026-09-03 재작업: 원래는 화면 설계용 목업(가짜 mockResult(), "청년주택드림
// 디딤돌대출"/"신생아 특례" 등 이 앱에 계산 로직이 없는 상품 3개 선택지)이었는데,
// 실제 백엔드(savings_simulator/simulate_housing_loan)에 연결했다 — /savings 탭
// (HousingLoanSimulator)에 있던 것과 같은 실제 계산이다. 실제로 지원하는 건
// "전세(버팀목)"/"매매(디딤돌)" 둘뿐이라 상품 선택을 그 기준으로 바꿨다.
// 지역/생애최초 토글은 여전히 뺐다(백엔드가 안 받는다) — 나이도 저장된 프로필
// 값을 그대로 쓴다.
// 2026-09-06: 미혼/기혼 토글은 다시 넣었다. 이번엔 HousingLoanInput.is_married로
// 실제 백엔드까지 전달돼서 청년전용/신혼부부전용 상품 분기와 소득 집계(미혼=본인 /
// 기혼=부부합산)를 실제로 바꾼다 — 예전처럼 "결과에 반영 안 되는 거짓 토글"이
// 아니다. 값을 안 보내면 백엔드가 저장된 프로필 is_married로 폴백한다.

import { useEffect, useState } from "react";
import { Home, Landmark, TrendingDown } from "lucide-react";
import { getMe, simulateHousingLoan, type HousingLoanOutput } from "@/lib/api";
import { krwToManwon, manwonToKrw } from "@/lib/profileOptions";
import { formatApplicationPeriod } from "@/lib/policyFormat";
import PolicyDetailLink from "@/components/PolicyDetailLink";
import {
  BackButton,
  DisclaimerNote,
  NextButton,
  ResetButton,
  Segmented,
  SliderField,
  StepRail,
  WizardFrame,
  manwon,
  type WizardStep,
} from "./wizardUi";

type HousingType = "jeonse" | "purchase";
type MaritalStatus = "single" | "married";

const HOUSING_TYPE_OPTIONS: {
  value: HousingType;
  name: string;
  desc: string;
  meta: string;
}[] = [
  {
    value: "jeonse",
    name: "버팀목 전세자금대출",
    desc: "청년전용(만 19~34세, 연소득 5천만원 이하) 또는 신혼부부전용(부부합산 연소득 7,500만원 이하) — 전세보증금 대출",
    meta: "LTV 80% · 2026.08 고시 기준",
  },
  {
    value: "purchase",
    name: "디딤돌대출",
    desc: "내집마련(일반, 연소득 6천만원 이하) 또는 신혼부부전용(부부합산 연소득 8,500만원 이하) — 주택 구입자금 대출",
    meta: "LTV 70% · 2026.08 고시 기준",
  },
];

const LOAN_TERM_OPTIONS = [10, 15, 20, 30] as const;

const STEPS: WizardStep[] = [
  { label: "상품 선택", sub: "전세 · 매매" },
  { label: "정보 입력", sub: "내 조건 입력하기" },
  { label: "결과 확인", sub: "예상 대출 가능액" },
];

const DISCLAIMER =
  "LTV·소득구간·금리는 2026년 8월 고시 기준 실제 수치예요. 다만 생애최초 주택구입자 우대, 지방 주택 인하, " +
  "자녀 수 등 이 계산기가 반영하지 못한 조건이 있고 시중 비교 금리는 은행마다 달라 가정치예요\n 정확한 조건은 " +
  "주택도시기금 공고를 확인하세요.";

export default function LoanWizard() {
  const [step, setStep] = useState(0);
  const [housingType, setHousingType] = useState<HousingType | null>(null);
  const [maritalStatus, setMaritalStatus] = useState<MaritalStatus>("single");
  // 프로필에서 읽어온 본인/배우자 연소득(만원) — 미혼/기혼 토글을 바꿀 때 소득
  // 슬라이더를 다시 채우는 기준값으로 쓴다.
  const [profileSelfIncome, setProfileSelfIncome] = useState(0);
  const [profileSpouseIncome, setProfileSpouseIncome] = useState(0);
  const [income, setIncome] = useState(6000); // 만원 — 미혼이면 본인, 기혼이면 부부합산
  const [priceManwon, setPriceManwon] = useState(25000); // 만원
  const [selfCapital, setSelfCapital] = useState(5000); // 만원
  const [loanTermYears, setLoanTermYears] = useState<10 | 15 | 20 | 30>(30);
  const [result, setResult] = useState<HousingLoanOutput | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("token") ?? "";
    getMe(token)
      .then((me) => {
        const self = me.annual_income_krw ? krwToManwon(me.annual_income_krw) : 0;
        const spouse = me.spouse_annual_income_krw
          ? krwToManwon(me.spouse_annual_income_krw)
          : 0;
        setProfileSelfIncome(self);
        setProfileSpouseIncome(spouse);
        const married = !!me.is_married;
        setMaritalStatus(married ? "married" : "single");
        const seed = married ? self + spouse : self;
        if (seed > 0) setIncome(seed);
      })
      .catch(() => {});
  }, []);

  // 미혼/기혼을 바꾸면 소득 슬라이더가 뜻하는 값(본인 vs 부부합산)이 달라지므로
  // 프로필 기준값으로 다시 채운다.
  function handleMaritalChange(next: MaritalStatus) {
    setMaritalStatus(next);
    setIncome(
      next === "married"
        ? profileSelfIncome + profileSpouseIncome
        : profileSelfIncome,
    );
  }

  // 자기자본은 목표 가격을 넘을 수 없다. 슬라이더의 max를 목표가격에 실시간
  // 연동시키면(예전 방식) range가 계속 바뀌어서 손잡이 위치가 제멋대로 튀어
  // 보였다 — 대신 max는 고정해두고, 실제로 초과했을 때만 값을 깎는다.
  useEffect(() => {
    setSelfCapital((prev) => Math.min(prev, priceManwon));
  }, [priceManwon]);

  const loanNeededManwon = Math.max(priceManwon - selfCapital, 0);

  async function handleSubmit() {
    if (!housingType) return;
    setError(null);
    setLoading(true);
    try {
      const token = localStorage.getItem("token") ?? "";
      const output = await simulateHousingLoan(token, {
        housing_type: housingType,
        target_price_krw: manwonToKrw(priceManwon),
        self_capital_krw: manwonToKrw(selfCapital),
        household_annual_income_krw: manwonToKrw(income),
        loan_term_years: loanTermYears,
        is_married: maritalStatus === "married",
      });
      setResult(output);
      setStep(2);
    } catch (err) {
      setError(err instanceof Error ? err.message : "계산에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }

  const selectedProduct =
    HOUSING_TYPE_OPTIONS.find((o) => o.value === housingType) ?? null;

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
              <NextButton
                label="다음"
                onClick={() => setStep(1)}
                disabled={!housingType}
              />
            </>
          }
        >
          <div className="grid gap-3">
            {HOUSING_TYPE_OPTIONS.map((o) => {
              const selected = o.value === housingType;
              return (
                <button
                  key={o.value}
                  type="button"
                  onClick={() => setHousingType(o.value)}
                  className={`flex items-center justify-between gap-4 rounded-2xl border p-5 text-left transition ${
                    selected
                      ? "border-[#b5623a] bg-[#fdf1ea]"
                      : "border-slate-200 bg-white hover:border-slate-300"
                  }`}
                >
                  <div>
                    <div className="text-[14px] font-extrabold text-ink">
                      {o.name}
                    </div>
                    <p className="mt-1 text-[12px] leading-5 text-slate-500">
                      {o.desc}
                    </p>
                    <div className="mt-1.5 text-[11px] font-semibold text-slate-400">
                      {o.meta}
                    </div>
                  </div>
                  <span
                    className={`shrink-0 rounded-full border px-4 py-1.5 text-[12px] font-extrabold ${
                      selected
                        ? "border-[#b5623a] text-[#b5623a]"
                        : "border-slate-300 text-slate-400"
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

      {step === 1 && selectedProduct && (
        <WizardFrame
          eyebrow="대출 시뮬레이터 · 2단계"
          title="내 조건을 입력해주세요"
          footer={
            <>
              <BackButton onClick={() => setStep(0)} />
              <NextButton
                label={loading ? "계산 중..." : "결과 보기"}
                onClick={handleSubmit}
                disabled={loading}
              />
            </>
          }
        >
          <div className="mb-6">
            <div className="mb-2 text-[12px] font-extrabold text-slate-700">
              혼인 여부
            </div>
            <Segmented
              options={[
                { value: "single", label: "미혼" },
                { value: "married", label: "기혼" },
              ]}
              value={maritalStatus}
              onChange={handleMaritalChange}
            />
            <p className="mt-1.5 text-[11px] font-semibold text-slate-400">
              미혼은 본인 소득만, 기혼은 부부 합산 소득으로 계산해요 · 청년전용 /
              신혼부부전용 상품도 이 선택으로 갈려요
            </p>
          </div>
          <div className="grid gap-6 sm:grid-cols-2">
            <SliderField
              label={
                maritalStatus === "married" ? "부부 합산 연소득" : "본인 연소득"
              }
              min={0}
              max={15000}
              step={100}
              value={income}
              onChange={setIncome}
            />
            <SliderField
              label={
                housingType === "jeonse" ? "목표 보증금" : "목표 주택 가격"
              }
              min={1000}
              max={90000}
              step={1000}
              value={priceManwon}
              onChange={setPriceManwon}
            />
            <div>
              <SliderField
                label="보유 자기자본"
                min={0}
                max={90000}
                step={500}
                value={selfCapital}
                onChange={setSelfCapital}
              />
              <p className="mt-1.5 text-[11px] font-semibold text-slate-400">
                자기자본은 목표 {housingType === "jeonse" ? "보증금" : "가격"}을
                넘을 수 없어요 · 필요 대출액{" "}
                <span className="font-extrabold text-[#0d1b36]">
                  {manwon(loanNeededManwon)}
                </span>
              </p>
            </div>
            {housingType === "purchase" ? (
              <div>
                <div className="mb-2 text-[12px] font-extrabold text-slate-700">
                  대출 기간
                </div>
                <div className="grid grid-cols-4 gap-2">
                  {LOAN_TERM_OPTIONS.map((y) => (
                    <button
                      key={y}
                      type="button"
                      onClick={() => setLoanTermYears(y)}
                      className={`h-12 rounded-xl border text-[12px] font-extrabold transition ${
                        loanTermYears === y
                          ? "border-[#0d1b36] bg-white text-[#0d1b36]"
                          : "border-slate-200 bg-white text-slate-400"
                      }`}
                    >
                      {y}년
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div />
            )}
          </div>
          {error && (
            <p className="mt-4 text-[13px] font-bold text-rose-500">{error}</p>
          )}
        </WizardFrame>
      )}

      {step === 2 && result && (
        <WizardFrame
          eyebrow="대출 시뮬레이터 · 3단계"
          title="예상 대출 가능액"
          footer={
            <>
              <div className="flex items-center gap-1">
                <BackButton onClick={() => setStep(1)} />
                <ResetButton onClick={() => setStep(0)} />
              </div>
              <span />
            </>
          }
        >
          <div className="rounded-2xl bg-[#0d1b36] p-6 text-white sm:p-7">
            <div className="flex items-center gap-2 text-[10px] font-extrabold uppercase tracking-[.18em] text-[#9cc5ff]">
              <Home size={13} /> {result.product_name}
            </div>
            <h3 className="mt-3 text-[20px] font-extrabold tracking-[-.04em] sm:text-[24px]">
              {result.summary}
            </h3>
            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl bg-white/10 p-3.5">
                <div className="text-[10px] font-bold text-blue-100/60">
                  정책 대출 가능액 (LTV {(result.ltv_rate * 100).toFixed(0)}%)
                </div>
                <div className="mt-2 text-[15px] font-extrabold">
                  {result.loan_amount_krw.toLocaleString()}원
                </div>
              </div>
              <div className="rounded-xl bg-white/10 p-3.5">
                <div className="text-[10px] font-bold text-blue-100/60">
                  정책 금리 연 {(result.policy_rate * 100).toFixed(2)}%
                </div>
                <div className="mt-2 text-[15px] font-extrabold">
                  월 {result.monthly_interest_krw.toLocaleString()}원
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-5">
            <div className="flex items-center gap-3">
              <span className="grid h-9 w-9 place-items-center rounded-xl bg-[#e6f8f5] text-[#159c8d]">
                <TrendingDown size={17} />
              </span>
              <div>
                <div className="text-[10px] font-extrabold uppercase tracking-[.18em] text-[#1eb8a6]">
                  SAVINGS
                </div>
                <div className="text-[14px] font-extrabold tracking-[-.03em] text-ink">
                  시중 대비 절감
                </div>
              </div>
            </div>
            <div className="mt-4 grid gap-3">
              <div className="rounded-xl bg-[#f7f9fc] px-4 py-3.5">
                <div className="text-[11px] font-bold text-slate-500">
                  시중 상품 월 이자 (연 {(result.market_rate * 100).toFixed(1)}
                  %)
                </div>
                <div className="mt-1 text-[14px] font-extrabold text-ink">
                  {result.market_monthly_interest_krw.toLocaleString()}원
                </div>
              </div>
              <div className="rounded-xl bg-[#e6f8f5] px-4 py-3.5">
                <div className="text-[11px] font-bold text-[#159c8d]">
                  월 이자 절감액
                </div>
                <div className="mt-1 text-[17px] font-extrabold text-[#159c8d]">
                  {result.monthly_saving_krw.toLocaleString()}원
                </div>
              </div>
            </div>
          </div>

          {result.matched_policies.length > 0 && (
            <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-5">
              <div className="flex items-center gap-2 text-[10px] font-extrabold uppercase tracking-[.18em] text-[#2457d6]">
                <Landmark size={12} /> 실제 정책 매칭
              </div>
              <div className="mt-1 text-[14px] font-extrabold tracking-[-.03em] text-ink">
                지금 내 조건으로 신청 가능한 대출이자 지원 정책
              </div>
              <div className="mt-4 grid gap-3">
                {result.matched_policies.map((p) => (
                  <div
                    key={p.policy_key}
                    className="rounded-xl border border-slate-200/80 bg-[#f7f9fc] p-4"
                  >
                    <div className="text-[13px] font-extrabold text-ink">
                      {p.policy_name}
                    </div>
                    <p className="mt-1.5 text-[12px] leading-5 text-slate-500">
                      {p.benefit_description}
                    </p>
                    <div className="mt-1.5 text-[11px] font-semibold text-slate-400">
                      신청 기간 {formatApplicationPeriod(p.application_period)}
                    </div>
                    <PolicyDetailLink
                      url={p.reference_url}
                      className="mt-1.5"
                    />
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
