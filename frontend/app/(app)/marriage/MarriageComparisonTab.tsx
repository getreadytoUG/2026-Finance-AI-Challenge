"use client";

import { useEffect, useState } from "react";
import { AlertCircle, ChevronDown, ChevronUp, Heart, Home, Info, Minus, Plus, Sparkles, Users } from "lucide-react";
import { SectionLabel } from "@/components/DashboardLayout";
import Pagination from "@/components/Pagination";
import PolicyDetailLink from "@/components/PolicyDetailLink";
import StatCard from "@/components/StatCard";
import {
  compareMarriageScenarios,
  getMe,
  rankMarriagePolicies,
  type HousingLoanMarriageComparison,
  type MarriageComparisonOutput,
  type MarriagePolicyItem,
} from "@/lib/api";
import { REGIONS, krwToManwon, manwonToKrw } from "@/lib/profileOptions";
import { formatApplicationPeriod } from "@/lib/policyFormat";

const PAGE_SIZE = 4;

type BucketKey = "married" | "unmarried" | "both";

function pillClass(active: boolean) {
  return `rounded-lg px-3.5 py-2 text-[11px] font-extrabold transition ${
    active ? "bg-[#2457d6] text-white" : "bg-[#eef3f9] text-slate-500 hover:bg-[#e3eaf6]"
  }`;
}

function PolicyRow({
  item,
  iconVariant,
  reason,
}: {
  item: MarriagePolicyItem;
  iconVariant: "violet" | "sky" | "mint";
  reason?: string;
}) {
  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-slate-200/80 bg-white p-5 sm:flex-row sm:items-center">
      <span className={`policy-list-icon ${iconVariant}`}>
        <Heart size={18} />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          {item.is_newlywed_policy && (
            <span className="policy-status available">
              <span />
              신혼부부
            </span>
          )}
          <span className="text-[15px] font-extrabold tracking-[-.03em] text-ink">{item.policy_name}</span>
        </div>
        <p className="mt-2 text-[12px] leading-5 text-slate-500">{item.benefit_description}</p>
        <div className="mt-2 text-[11px] font-semibold text-slate-400">신청 기간 {formatApplicationPeriod(item.application_period)}</div>
        {item.change_reason && (
          <div className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-[#f5f8fd] px-2.5 py-1.5 text-[11px] font-bold text-slate-500">
            <AlertCircle size={12} className="shrink-0 text-[#2457d6]" />
            {item.change_reason}
          </div>
        )}
        <PolicyDetailLink url={item.reference_url} className="mt-2" />
        {reason && (
          <div className="mt-3 rounded-xl bg-[#f7f9fc] p-3 text-[12px] leading-relaxed text-slate-600">
            <span className="font-extrabold text-[#2457d6]">AI 우선순위 코멘트</span> · {reason}
          </div>
        )}
      </div>
    </div>
  );
}

// order에 담긴 policy_key 순서대로 재배열한다. AI 정렬 전(order===null)이면 원래 순서 그대로.
function orderedItems(items: MarriagePolicyItem[], order: string[] | null): MarriagePolicyItem[] {
  if (!order) return items;
  const byKey = new Map(items.map((item) => [item.policy_key, item]));
  const seen = new Set<string>();
  const ranked: MarriagePolicyItem[] = [];
  for (const key of order) {
    const item = byKey.get(key);
    if (item) {
      ranked.push(item);
      seen.add(key);
    }
  }
  // 방어적으로, order에 없는 항목(이론상 없어야 함)은 뒤에 그대로 붙인다.
  return [...ranked, ...items.filter((item) => !seen.has(item.policy_key))];
}

// 세 버킷 공통: 4개씩 페이지네이션 + "해당 없음" 처리를 한 곳에서 담당한다.
function PolicyBucket({
  items,
  order,
  reasons,
  page,
  onPageChange,
  iconVariant,
}: {
  items: MarriagePolicyItem[];
  order: string[] | null;
  reasons: Record<string, string>;
  page: number;
  onPageChange: (page: number) => void;
  iconVariant: "violet" | "sky" | "mint";
}) {
  if (items.length === 0) {
    return <p className="text-[13px] font-bold text-slate-400">해당하는 정책이 없어요.</p>;
  }
  const sorted = orderedItems(items, order);
  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  const pageItems = sorted.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  return (
    <>
      <div className="grid gap-3">
        {pageItems.map((item) => (
          <PolicyRow key={item.policy_key} item={item} iconVariant={iconVariant} reason={reasons[item.policy_key]} />
        ))}
      </div>
      <Pagination page={page} totalPages={totalPages} onPageChange={onPageChange} />
    </>
  );
}

function RankButton({
  onClick,
  loading,
  disabled,
}: {
  onClick: () => void;
  loading: boolean;
  disabled: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled || loading}
      className="inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-[#eef3ff] px-3 py-1.5 text-[11px] font-extrabold text-[#2457d6] transition hover:bg-[#e3eaf6] disabled:opacity-50"
    >
      <Sparkles size={13} />
      {loading ? "정렬 중..." : "AI로 우선순위 정렬"}
    </button>
  );
}

// 2026-09-03 추가("혼인신고 계산기도 특정 정책 타겟팅해야 함", 사용자 요청): 정책
// DB 전체 스캔 대신, 실제로 미혼용/기혼용 상품이 이름부터 따로 있는 고정 기준
// 2개(버팀목 전세자금대출/디딤돌대출)의 실제 조건 차이를 항상 먼저 보여준다.
function HousingComparisonCard({ comparison }: { comparison: HousingLoanMarriageComparison }) {
  const title = comparison.housing_type === "jeonse" ? "전세자금대출" : "구입자금대출(디딤돌)";
  const columns: { label: string; tone: "unmarried" | "married"; scenario: HousingLoanMarriageComparison["unmarried"] }[] = [
    { label: "미혼", tone: "unmarried", scenario: comparison.unmarried },
    { label: "기혼", tone: "married", scenario: comparison.married },
  ];
  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white p-5">
      <div className="flex items-center gap-2">
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[#eef3ff] text-[#2457d6]">
          <Home size={15} />
        </span>
        <div className="text-[13px] font-extrabold text-ink">{title}</div>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3">
        {columns.map(({ label, tone, scenario }) => (
          <div key={tone} className={`rounded-xl p-4 ${tone === "married" ? "bg-[#eef3ff]" : "bg-[#f7f9fc]"}`}>
            <div className={`text-[10px] font-bold ${tone === "married" ? "text-[#2457d6]" : "text-slate-400"}`}>{label}</div>
            <div className="mt-1 text-[12px] font-extrabold leading-5 text-ink">{scenario.product_name}</div>
            {scenario.eligible ? (
              <>
                <div className="mt-2 text-[19px] font-extrabold text-[#2457d6]">연 {(scenario.policy_rate * 100).toFixed(2)}%</div>
                <div className="mt-1 text-[11px] font-semibold text-slate-500">
                  대출 가능액 {scenario.loan_amount_krw.toLocaleString()}원 · 월 이자 약 {scenario.monthly_interest_krw.toLocaleString()}원
                </div>
              </>
            ) : (
              <div className="mt-2 text-[12px] font-bold text-rose-500">대상 아님</div>
            )}
            <p className="mt-2 text-[11px] leading-5 text-slate-500">{scenario.summary}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function MarriageComparisonTab() {
  const [age, setAge] = useState("29");
  const [income, setIncome] = useState("4000");
  const [region, setRegion] = useState("서울");
  const [spouseIncome, setSpouseIncome] = useState("");
  const [targetPrice, setTargetPrice] = useState("25000");
  const [selfCapital, setSelfCapital] = useState("5000");
  const [result, setResult] = useState<MarriageComparisonOutput | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const [marriedPage, setMarriedPage] = useState(1);
  const [unmarriedPage, setUnmarriedPage] = useState(1);
  const [bothPage, setBothPage] = useState(1);
  const [showBoth, setShowBoth] = useState(false);

  // AI 정렬 결과 — 버킷별 policy_key 순서와, policy_key별 한 줄 코멘트.
  const [rankOrder, setRankOrder] = useState<Record<BucketKey, string[] | null>>({ married: null, unmarried: null, both: null });
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [rankingBucket, setRankingBucket] = useState<BucketKey | null>(null);
  const [rankError, setRankError] = useState<Record<BucketKey, string | null>>({ married: null, unmarried: null, both: null });

  useEffect(() => {
    const token = localStorage.getItem("token") ?? "";
    getMe(token)
      .then((me) => {
        if (me.age != null) setAge(String(me.age));
        if (me.annual_income_krw != null) setIncome(String(krwToManwon(me.annual_income_krw)));
        if (me.region != null) setRegion(me.region);
        if (me.spouse_annual_income_krw != null) setSpouseIncome(String(krwToManwon(me.spouse_annual_income_krw)));
      })
      .catch(() => {});
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    setMarriedPage(1);
    setUnmarriedPage(1);
    setBothPage(1);
    setShowBoth(false);
    setRankOrder({ married: null, unmarried: null, both: null });
    setReasons({});
    setRankError({ married: null, unmarried: null, both: null });
    setLoading(true);
    const token = localStorage.getItem("token") ?? "";
    try {
      const output = await compareMarriageScenarios(token, {
        age: Number(age),
        region,
        annual_income_krw: manwonToKrw(Number(income)),
        spouse_annual_income_krw: spouseIncome ? manwonToKrw(Number(spouseIncome)) : null,
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

  async function handleRank(bucket: BucketKey, items: MarriagePolicyItem[], contextLabel: string) {
    if (items.length === 0) return;
    setRankingBucket(bucket);
    setRankError((prev) => ({ ...prev, [bucket]: null }));
    const token = localStorage.getItem("token") ?? "";
    try {
      const output = await rankMarriagePolicies(token, {
        age: Number(age),
        region,
        annual_income_krw: manwonToKrw(Number(income)),
        spouse_annual_income_krw: spouseIncome ? manwonToKrw(Number(spouseIncome)) : null,
        policy_keys: items.map((item) => item.policy_key),
        context_label: contextLabel,
      });
      setRankOrder((prev) => ({ ...prev, [bucket]: output.ranked.map((r) => r.policy_key) }));
      setReasons((prev) => {
        const next = { ...prev };
        for (const r of output.ranked) next[r.policy_key] = r.reason;
        return next;
      });
      if (bucket === "married") setMarriedPage(1);
      if (bucket === "unmarried") setUnmarriedPage(1);
      if (bucket === "both") setBothPage(1);
    } catch (err) {
      setRankError((prev) => ({ ...prev, [bucket]: err instanceof Error ? err.message : "정렬에 실패했습니다." }));
    } finally {
      setRankingBucket(null);
    }
  }

  const showSpouseHint = result && result.married_only.length === 0 && result.unmarried_only.length === 0 && !spouseIncome;

  return (
    <div>
      <div className="mb-6 flex items-start gap-3 rounded-2xl border border-slate-200/80 bg-white p-4">
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[#eef3ff] text-[#2457d6]">
          <Info size={17} />
        </span>
        <div>
          <div className="text-[13px] font-extrabold text-ink">실제 정책 데이터 기준 비교입니다</div>
          <p className="mt-1 text-[12px] leading-5 text-slate-500">
            {/* 2026-09-03 재작업("혼인신고 계산기도 특정 정책 타겟팅해야 함", 사용자
                요청): 정책 DB 2,750건을 통째로 스캔해 자격 변화를 찾는 방식은 실제로
                혼인상태를 조건으로 거는 정책이 71건뿐이라 대부분 밋밋한 결과만 냈다.
                실제로 미혼용/기혼용 상품이 이름부터 따로 있는 걸로 확인된 고정 기준
                2개를 항상 먼저 비교한다(marriage_comparison.compare_housing_loan_scenarios
                참고). */}
            혼인 여부에 따라 조건이 실제로 달라지는 국가 주택금융 상품 2가지를 고정 기준으로 비교해요 —
            전세는 <b>[미혼] 청년전용 버팀목 전세자금대출</b> vs <b>[기혼] 신혼부부전용 버팀목 전세자금대출</b>,
            매매는 <b>[미혼] 내집마련 디딤돌대출</b> vs <b>[기혼] 신혼부부전용 디딤돌대출</b>로 소득상한·금리·
            대출한도를 나란히 보여드려요. 그 아래는 그 외 정책 중 배우자 소득 합산(대부분) 또는 혼인상태
            조건(2,750건 중 71건) 때문에 자격이 달라지는 것들이에요. &quot;AI로 우선순위 정렬&quot;은 정책
            설명을 AI가 읽고 판단한 추천 순서이며, 실제 심사 결과와 다를 수 있어요.
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
          <div className="grid gap-2 text-[12px] font-extrabold text-slate-700 sm:col-span-2">
            지역
            {/* 2026-09-03 사용자 요청으로 자유 텍스트 입력을 REGIONS 목록 선택으로
                바꿨다 — 목록에 없는 표기("전라도" 등)를 입력하면 matching.region_matches가
                안전한 쪽으로 fail-open(필터링 없이 통과)해버려서, 지역을 입력해도
                실제로는 전혀 안 걸러지는 조용한 버그가 있었다(ProfileFieldsForm/
                AiSearchFilterBar와 동일하게 REGIONS 고정 목록만 고르게 강제한다). */}
            <div className="flex flex-wrap gap-2">
              {REGIONS.map((r) => (
                <button key={r} type="button" className={pillClass(region === r)} onClick={() => setRegion(r)}>
                  {r}
                </button>
              ))}
            </div>
          </div>
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

      {error && <p className="mt-4 text-[13px] font-bold text-rose-500">{error}</p>}

      {showSpouseHint && (
        <p className="mt-4 text-[12px] font-bold text-slate-400">
          배우자(예정) 소득을 입력하면 더 정확한 비교를 볼 수 있어요.
        </p>
      )}

      {result && (
        <div className="mt-6">
          {/* 고정 기준 상품 비교 — 이 탭의 핵심. DB 스캔 버킷(아래)보다 먼저, 항상
              보여준다(2026-09-03 사용자 요청). */}
          <div className="mb-3 text-[13px] font-extrabold text-ink">기준 정책 비교</div>
          <div className="grid gap-3 sm:grid-cols-2">
            {result.housing_loan_comparisons.map((c) => (
              <HousingComparisonCard key={c.housing_type} comparison={c} />
            ))}
          </div>

          {/* 결과를 한눈에 — 아래 목록을 하나씩 읽지 않아도 핵심 숫자가 바로 보이도록. */}
          <div className="mb-3 mt-8 text-[13px] font-extrabold text-ink">그 외 정책 중 자격이 달라지는 것</div>
          <div className="grid gap-3 sm:grid-cols-3">
            <StatCard
              label="혼인신고 후 새로 자격됨"
              value={`${result.married_only.length}개`}
              detail="지금은 안 되지만 결혼하면 가능"
              tone="violet"
            />
            <StatCard
              label="미혼일 때만 자격됨"
              value={`${result.unmarried_only.length}개`}
              detail="결혼하면 자격을 잃는 정책"
              tone="sky"
            />
            <StatCard
              label="혼인 여부와 무관"
              value={`${result.both.length}개`}
              detail="둘 다 자격되는 정책"
              tone="mint"
            />
          </div>

          <div className="mt-8 grid gap-8">
            <div>
              <SectionLabel
                action={
                  <RankButton
                    onClick={() => handleRank("married", result.married_only, "혼인신고 후에만 자격되는 정책")}
                    loading={rankingBucket === "married"}
                    disabled={rankingBucket !== null || result.married_only.length === 0}
                  />
                }
              >
                <span className="inline-flex items-center gap-1.5">
                  <Plus size={14} className="text-[#6252d7]" /> 혼인신고 후에만 자격됨
                </span>
              </SectionLabel>
              <p className="-mt-2 mb-3 text-[12px] text-slate-500">지금 프로필로는 자격이 안 되지만, 혼인신고 후 가구소득 합산 기준으로 바뀌면 신청할 수 있는 정책이에요.</p>
              {rankError.married && <p className="mb-3 text-[12px] font-bold text-rose-500">{rankError.married}</p>}
              <PolicyBucket
                items={result.married_only}
                order={rankOrder.married}
                reasons={reasons}
                page={marriedPage}
                onPageChange={setMarriedPage}
                iconVariant="violet"
              />
            </div>
            <div>
              <SectionLabel
                action={
                  <RankButton
                    onClick={() => handleRank("unmarried", result.unmarried_only, "미혼일 때만 자격되는 정책")}
                    loading={rankingBucket === "unmarried"}
                    disabled={rankingBucket !== null || result.unmarried_only.length === 0}
                  />
                }
              >
                <span className="inline-flex items-center gap-1.5">
                  <Minus size={14} className="text-[#1689b7]" /> 미혼일 때만 자격됨
                </span>
              </SectionLabel>
              <p className="-mt-2 mb-3 text-[12px] text-slate-500">지금은 자격이 되지만, 혼인신고 후 가구소득이 합산되면 소득 상한을 넘어 자격을 잃는 정책이에요.</p>
              {rankError.unmarried && <p className="mb-3 text-[12px] font-bold text-rose-500">{rankError.unmarried}</p>}
              <PolicyBucket
                items={result.unmarried_only}
                order={rankOrder.unmarried}
                reasons={reasons}
                page={unmarriedPage}
                onPageChange={setUnmarriedPage}
                iconVariant="sky"
              />
            </div>

            {/* 변화가 없는(가장 길고 덜 중요한) 목록은 기본으로 접어둔다 — 위 두 목록이 이 탭의
                실제 요점이라, 항상 펼쳐두면 오히려 핵심이 묻혀서 "알아보기 어렵다"는 문제가 됐다. */}
            <div>
              <button
                type="button"
                onClick={() => setShowBoth((v) => !v)}
                className="flex w-full items-center justify-between rounded-2xl border border-slate-200/80 bg-white px-5 py-4 text-left transition hover:border-[#cddafb]"
              >
                <span className="inline-flex items-center gap-2 text-[13px] font-extrabold text-ink">
                  <Users size={15} className="text-slate-400" />
                  혼인 여부와 무관하게 둘 다 해당 ({result.both.length})
                </span>
                {showBoth ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />}
              </button>
              {showBoth && (
                <div className="mt-3">
                  <div className="mb-3 flex justify-end">
                    <RankButton
                      onClick={() => handleRank("both", result.both, "혼인 여부와 무관하게 둘 다 자격되는 정책")}
                      loading={rankingBucket === "both"}
                      disabled={rankingBucket !== null || result.both.length === 0}
                    />
                  </div>
                  {rankError.both && <p className="mb-3 text-[12px] font-bold text-rose-500">{rankError.both}</p>}
                  <PolicyBucket
                    items={result.both}
                    order={rankOrder.both}
                    reasons={reasons}
                    page={bothPage}
                    onPageChange={setBothPage}
                    iconVariant="mint"
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
