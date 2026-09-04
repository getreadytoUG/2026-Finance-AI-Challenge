"use client";

// 정책연계 저축계좌상품 시뮬레이터 — 상품 선택 → 조건 입력 → 예상 만기수령액.
// 2026-09-04: 사용자 지적("왜 니맘대로 3개 선택지를 없애냐")으로 원래 있던 상품
// 선택 3개(청년미래적금/청년도약계좌 기존가입자/청년주택드림청약통장)를 되살렸다.
// 이 앱에 실제 계산 로직이 있는 건 청년미래적금 하나뿐이라(다른 둘은 백엔드
// savings_simulator에 대응 함수가 없음) 그것만 실제 백엔드(simulate_youth_future_savings)를
// 부르고, 나머지 둘은 원래 목업 그대로 화면 설계용 예시 수치(mockResult)를 쓴다 —
// 어느 쪽인지 상품 카드와 결과 화면 양쪽에 명시해서 혼동을 막는다.

import { useEffect, useState } from "react";
import { PiggyBank, TrendingUp } from "lucide-react";
import { getMe, simulateYouthFutureSavings, type YouthFutureSavingsOutput } from "@/lib/api";
import { krwToManwon, manwonToKrw } from "@/lib/profileOptions";
import { formatApplicationPeriod } from "@/lib/policyFormat";
import NoteTooltip from "@/components/NoteTooltip";
import PolicyDetailLink from "@/components/PolicyDetailLink";
import {
  BackButton,
  DisclaimerNote,
  NextButton,
  PrelimRow,
  Segmented,
  SliderField,
  StepRail,
  WizardFrame,
  manwon,
  type WizardStep,
} from "./wizardUi";

type SavingsProduct = {
  id: string;
  name: string;
  desc: string;
  meta: string;
  termMonths: number;
  monthlyCapManwon: number;
  matchGeneral: number; // 일반형 정부매칭 비율 (0이면 금리형 상품)
  matchPreferential: number; // 우대형(중소기업 재직) 매칭 비율
  savingsRate: number; // 예시 적용 금리 (비과세)
  real: boolean; // true면 실제 백엔드 계산, false면 화면 설계용 예시(mockResult)
};

const PRODUCTS: SavingsProduct[] = [
  {
    id: "future",
    name: "청년미래적금",
    desc: "만 19~34세 청년 대상, 월 최대 50만원 납입 시 정부가 납입금의 6~12%를 매칭 지원",
    meta: "3년 만기 · 2026.08 기준 · 실제 계산",
    termMonths: 36,
    monthlyCapManwon: 50,
    matchGeneral: 0.06,
    matchPreferential: 0.12,
    savingsRate: 0.045,
    real: true,
  },
  {
    id: "leap",
    name: "청년도약계좌 (기존 가입자)",
    desc: "2025년 신규가입 종료, 기존 가입자는 만기까지 기여금·비과세 유지",
    meta: "5년 만기 · 2026.08 기준 · 예시 수치",
    termMonths: 60,
    monthlyCapManwon: 70,
    matchGeneral: 0.033,
    matchPreferential: 0.06,
    savingsRate: 0.045,
    real: false,
  },
  {
    id: "dream",
    name: "청년주택드림 청약통장",
    desc: "최고 연 4.5% 금리 + 이자소득 비과세, 청약 당첨 시 대출 연계",
    meta: "수시입출 · 2026.08 기준 · 예시 수치",
    termMonths: 24,
    monthlyCapManwon: 100,
    matchGeneral: 0,
    matchPreferential: 0,
    savingsRate: 0.045,
    real: false,
  },
];

const STEPS: WizardStep[] = [
  { label: "상품 선택", sub: "저축상품 고르기" },
  { label: "정보 입력", sub: "내 조건 입력하기" },
  { label: "결과 확인", sub: "예상 만기수령액" },
];

const MOCK_DISCLAIMER =
  "본 결과는 화면 설계용 예시 수치이며 실제 지급액과 다를 수 있습니다. 정확한 조건·매칭비율은 서민금융진흥원 및 주택도시기금 공고에서 다시 확인하세요.";

const REAL_DISCLAIMER =
  "매칭비율·소득구간은 2026년 6월 출시 공고 기준 실제 수치예요. 다만 가구 중위소득 조건은 반영하지 못했고, " +
  "시중적금 비교 금리는 은행마다 달라 가정치예요 — 정확한 조건은 서민금융진흥원 공고를 확인하세요.";

const YOUTH_LEAP_ACCOUNT_STATUS_NOTE =
  "청년도약계좌는 2025년 12월 31일자로 신규가입이 종료됐어요(기존 가입자는 만기까지 그대로 유지). " +
  "2026년 6월부터는 후속 상품인 청년미래적금이 정부기여금·비과세 혜택을 이어받았어요.";

// 예시 계산(청년도약계좌/청년주택드림 전용) — 단리 이자 근사 + 정부기여금 매칭. 단위는 전부 만원.
function mockResult(p: SavingsProduct, monthly: number, sme: boolean, income: number) {
  const preferential = sme && income <= 3600;
  const matchRate = preferential ? p.matchPreferential : p.matchGeneral;
  const matchedBase = Math.min(monthly, p.monthlyCapManwon);
  const n = p.termMonths;
  const principal = monthly * n;
  const govt = Math.round(matchedBase * matchRate * n);
  const interest = Math.round((monthly * (n * (n + 1)) / 2) * (p.savingsRate / 12));
  return {
    preferential,
    matchRate,
    principal,
    govt,
    interest,
    maturity: principal + govt + interest,
  };
}

export default function SavingsWizard() {
  const [step, setStep] = useState(0);
  const [productId, setProductId] = useState<string | null>(null);
  const [monthly, setMonthly] = useState(50);
  const [income, setIncome] = useState(3500);
  const [sme, setSme] = useState<"yes" | "no">("no");
  const [realResult, setRealResult] = useState<YouthFutureSavingsOutput | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("token") ?? "";
    getMe(token)
      .then((me) => {
        if (me.annual_income_krw != null) setIncome(krwToManwon(me.annual_income_krw));
      })
      .catch(() => {});
  }, []);

  const product = PRODUCTS.find((p) => p.id === productId) ?? null;

  function selectProduct(p: SavingsProduct) {
    setProductId(p.id);
    setMonthly((m) => Math.min(m, p.monthlyCapManwon));
  }

  async function handleShowResult() {
    if (!product) return;
    setError(null);
    if (!product.real) {
      setStep(2);
      return;
    }
    setLoading(true);
    try {
      const token = localStorage.getItem("token") ?? "";
      const output = await simulateYouthFutureSavings(token, {
        monthly_amount_krw: manwonToKrw(monthly),
        annual_income_krw: manwonToKrw(income),
        seed_money_krw: 0,
      });
      setRealResult(output);
      setStep(2);
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
          eyebrow="저축 시뮬레이터 · 1단계"
          title="어떤 저축상품을 확인해볼까요"
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
                  onClick={() => selectProduct(p)}
                  className={`flex items-center justify-between gap-4 rounded-2xl border p-5 text-left transition ${
                    selected ? "border-[#2f7a3f] bg-[#eef7ee]" : "border-slate-200 bg-white hover:border-slate-300"
                  }`}
                >
                  <div>
                    <div className="text-[14px] font-extrabold text-ink">{p.name}</div>
                    <p className="mt-1 text-[12px] leading-5 text-slate-500">{p.desc}</p>
                    <div className="mt-1.5 text-[11px] font-semibold text-slate-400">{p.meta}</div>
                  </div>
                  <span
                    className={`shrink-0 rounded-full border px-4 py-1.5 text-[12px] font-extrabold ${
                      selected ? "border-[#2f7a3f] text-[#2f7a3f]" : "border-slate-300 text-slate-400"
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
          eyebrow="저축 시뮬레이터 · 2단계"
          title="내 조건을 입력해주세요"
          footer={
            <>
              <BackButton onClick={() => setStep(0)} />
              <NextButton label={loading ? "계산 중..." : "결과 보기"} onClick={handleShowResult} disabled={loading} />
            </>
          }
        >
          <div className="grid gap-6 sm:grid-cols-2">
            <SliderField
              label="월 납입액"
              valueLabel={manwon(monthly)}
              min={10}
              max={product.monthlyCapManwon}
              step={5}
              value={monthly}
              onChange={setMonthly}
            />
            <SliderField
              label="본인 연소득"
              valueLabel={manwon(income)}
              min={0}
              max={9000}
              step={100}
              value={income}
              onChange={setIncome}
            />
            <div>
              <div className="mb-2 text-[12px] font-extrabold text-slate-700">중소기업 재직 여부</div>
              <Segmented
                options={[
                  { value: "yes", label: "재직 중" },
                  { value: "no", label: "해당 없음" },
                ]}
                value={sme}
                onChange={setSme}
              />
              {product.real && (
                <p className="mt-2 text-[11px] font-semibold text-slate-400">
                  청년미래적금은 저장된 프로필의 재직 여부를 기준으로 실제 계산돼요 — 이 토글은 예시 상품(청년도약계좌/청년주택드림)에만 적용돼요.
                </p>
              )}
            </div>
            <div>
              <div className="mb-2 text-[12px] font-extrabold text-slate-700">가입 기간</div>
              <div className="flex h-12 items-center rounded-xl bg-[#eef3f9] px-4 text-[13px] font-extrabold text-slate-500">
                {product.termMonths % 12 === 0 ? `${product.termMonths / 12}년 (고정)` : `${product.termMonths}개월 (고정)`}
              </div>
            </div>
          </div>

          <div className="mt-7 rounded-2xl border border-slate-200 bg-[#f7f9fc] px-5 py-2">
            <div className="py-2 text-[11px] font-extrabold uppercase tracking-[.16em] text-slate-400">자격 예비판정</div>
            <PrelimRow label="나이 조건 (만 19~34세)" ok />
            <PrelimRow label="소득 조건 (총급여 7,500만원 이하)" ok={income <= 7500} />
          </div>
          {error && <p className="mt-4 text-[13px] font-bold text-rose-500">{error}</p>}
        </WizardFrame>
      )}

      {step === 2 && product && (
        <WizardFrame
          eyebrow="저축 시뮬레이터 · 3단계"
          title="예상 만기수령액"
          footer={
            <>
              <BackButton onClick={() => setStep(1)} />
              <NextButton
                label="다른 상품 보기"
                onClick={() => {
                  setStep(0);
                  setProductId(null);
                  setRealResult(null);
                }}
              />
            </>
          }
        >
          {product.real ? (
            realResult && (
              <div>
                <div className="rounded-2xl bg-[#0d1b36] p-6 text-white sm:p-7">
                  <div className="flex items-center gap-2 text-[10px] font-extrabold uppercase tracking-[.18em] text-[#9cc5ff]">
                    <PiggyBank size={13} /> {product.name}
                    <NoteTooltip
                      text={YOUTH_LEAP_ACCOUNT_STATUS_NOTE}
                      triggerClassName="text-[#9cc5ff]/70 hover:text-[#9cc5ff]"
                      bubbleClassName="bg-white text-[#0d1b36] ring-1 ring-black/5"
                    />
                  </div>
                  <h3 className="mt-3 text-[24px] font-extrabold tracking-[-.05em] sm:text-[28px]">
                    {realResult.eligible ? (
                      <>
                        만기에 <span className="text-[#9cc5ff]">{manwon(krwToManwon(realResult.policy_total_krw))}</span>을 받을 수 있어요.
                      </>
                    ) : (
                      "이 상품은 지금 조건으로는 가입할 수 없어요."
                    )}
                  </h3>
                  <p className="mt-3 text-[12px] leading-6 text-blue-100/70">{realResult.eligibility_note}</p>
                  <div className="mt-6 grid gap-3 sm:grid-cols-2">
                    <div className="rounded-xl bg-white/10 p-3.5">
                      <div className="text-[10px] font-bold text-blue-100/60">청년미래적금 만기수령액</div>
                      <div className="mt-2 text-[15px] font-extrabold">{realResult.policy_total_krw.toLocaleString()}원</div>
                    </div>
                    <div className="rounded-xl bg-white/10 p-3.5">
                      <div className="text-[10px] font-bold text-blue-100/60">일반 시중적금(가정 금리 기준)</div>
                      <div className="mt-2 text-[15px] font-extrabold">{realResult.market_total_krw.toLocaleString()}원</div>
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
                    <div className={`mt-1 text-[18px] font-extrabold ${realResult.benefit_diff_krw > 0 ? "text-[#159c8d]" : "text-slate-500"}`}>
                      {realResult.benefit_diff_krw > 0 ? "+" : ""}
                      {realResult.benefit_diff_krw.toLocaleString()}원
                    </div>
                  </div>
                  <p className="mt-3 text-[12px] leading-5 text-slate-500">{realResult.summary}</p>
                </div>

                {realResult.matched_policies.length > 0 && (
                  <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-5">
                    <div className="text-[10px] font-extrabold uppercase tracking-[.18em] text-[#2457d6]">실제 정책 매칭</div>
                    <div className="mt-1 text-[14px] font-extrabold tracking-[-.03em] text-ink">지금 내 조건으로 신청 가능한 저축 정책</div>
                    <div className="mt-4 grid gap-3">
                      {realResult.matched_policies.map((p) => (
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

                <DisclaimerNote text={REAL_DISCLAIMER} />
              </div>
            )
          ) : (
            (() => {
              const r = mockResult(product, monthly, sme === "yes", income);
              return (
                <div>
                  <div className="rounded-2xl bg-[#f4f8f4] p-6">
                    <div className="flex items-center gap-2 text-[11px] font-extrabold uppercase tracking-[.16em] text-[#2f7a3f]">
                      <PiggyBank size={13} /> {product.name}
                    </div>
                    <div className="mt-2 text-[40px] font-extrabold tracking-[-.05em] text-[#2f7a3f]">{manwon(r.maturity)}</div>
                    <p className="mt-1 text-[12px] font-semibold text-slate-500">
                      {r.govt > 0
                        ? `정부기여금 약 ${manwon(r.govt)} + 비과세 이자 약 ${manwon(r.interest)} 포함 (예시)`
                        : `비과세 이자 약 ${manwon(r.interest)} 포함 · 금리형 상품이라 정부기여금은 없음 (예시)`}
                    </p>
                  </div>

                  <div className="mt-4 grid gap-4 sm:grid-cols-2">
                    <div className="rounded-2xl border border-slate-200 bg-white p-5">
                      <div className="text-[11px] font-bold text-slate-400">정부 매칭 비율</div>
                      <div className="mt-1.5 text-[20px] font-extrabold text-ink">
                        {r.matchRate > 0 ? `연 ${(r.matchRate * 100).toFixed(1)}%` : "해당 없음"}
                      </div>
                      <div className="mt-1 text-[11px] font-semibold text-slate-400">
                        {r.matchRate > 0 ? (r.preferential ? "우대형 (중소기업 재직)" : "일반형") : "금리형 상품"}
                      </div>
                    </div>
                    <div className="rounded-2xl border border-slate-200 bg-white p-5">
                      <div className="text-[11px] font-bold text-slate-400">총 납입 원금</div>
                      <div className="mt-1.5 text-[20px] font-extrabold text-ink">{manwon(r.principal)}</div>
                      <div className="mt-1 text-[11px] font-semibold text-slate-400">
                        월 {manwon(monthly)} × {product.termMonths}개월
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => setSme("no")}
                      className={`h-11 rounded-xl border text-[12px] font-extrabold transition ${
                        sme === "no" ? "border-[#0d1b36] bg-white text-[#0d1b36]" : "border-slate-200 bg-white text-slate-400"
                      }`}
                    >
                      일반형
                    </button>
                    <button
                      type="button"
                      onClick={() => setSme("yes")}
                      className={`h-11 rounded-xl border text-[12px] font-extrabold transition ${
                        sme === "yes" ? "border-[#0d1b36] bg-white text-[#0d1b36]" : "border-slate-200 bg-white text-slate-400"
                      }`}
                    >
                      우대형 (중소기업 재직)
                    </button>
                  </div>

                  <DisclaimerNote text={MOCK_DISCLAIMER} />
                </div>
              );
            })()
          )}
        </WizardFrame>
      )}
    </div>
  );
}
