"use client";

import { useEffect, useState } from "react";
import { ChevronDown, ChevronUp, Heart, Info, Minus, Plus, Sparkles, Users } from "lucide-react";
import { SectionLabel } from "@/components/DashboardLayout";
import Pagination from "@/components/Pagination";
import PolicyDetailLink from "@/components/PolicyDetailLink";
import StatCard from "@/components/StatCard";
import {
  compareMarriageScenarios,
  getMe,
  rankMarriagePolicies,
  type MarriageComparisonOutput,
  type MarriagePolicyItem,
} from "@/lib/api";
import { krwToManwon, manwonToKrw } from "@/lib/profileOptions";

const PAGE_SIZE = 4;

type BucketKey = "married" | "unmarried" | "both";

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
        <div className="mt-2 text-[11px] font-semibold text-slate-400">신청 기간 {item.application_period}</div>
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

export default function MarriageComparisonTab() {
  const [age, setAge] = useState("29");
  const [income, setIncome] = useState("4000");
  const [region, setRegion] = useState("서울");
  const [spouseIncome, setSpouseIncome] = useState("");
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
            혼인신고 전(미혼)과 후(부부합산소득) 시나리오로 지금 정책 데이터를 두 번 조회해 자격이 달라지는
            정책만 보여줘요. 청약 가점, 대출 금리 데이터는 포함하지 않습니다. &quot;AI로 우선순위 정렬&quot;은
            정책 설명을 AI가 읽고 판단한 추천 순서이며, 실제 심사 결과와 다를 수 있어요.
            {/* 2026-09-02 QA에서 발견: 원본 API의 혼인상태 코드를 기혼/미혼으로 매핑하지
                못해(matching.py 참고) 대부분 정책은 소득 변화로만 자격이 갈린다 — 배우자
                소득을 안 넣으면 두 시나리오가 똑같아 위 두 항목이 항상 0개로 나올 수
                있다는 걸 미리 알려준다. */}{" "}
            현재는 소득 조건 변화(배우자 소득 합산)로만 자격 변화가 반영돼요 — 혼인 여부 자체를
            조건으로 거는 정책은 아직 구분해내지 못해, 배우자 소득을 안 넣으면 두 시나리오가 같게
            나올 수 있어요.
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
            지역
            <input
              type="text"
              value={region}
              onChange={(e) => setRegion(e.target.value)}
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
          {/* 결과를 한눈에 — 아래 목록을 하나씩 읽지 않아도 핵심 숫자가 바로 보이도록. */}
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
