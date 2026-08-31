"use client";

import { useEffect, useState } from "react";
import { Heart, Info, Users } from "lucide-react";
import { SectionLabel } from "@/components/DashboardLayout";
import PolicyDetailLink from "@/components/PolicyDetailLink";
import {
  compareMarriageScenarios,
  getMe,
  type MarriageComparisonOutput,
  type MarriagePolicyItem,
} from "@/lib/api";
import { krwToManwon, manwonToKrw } from "@/lib/profileOptions";

function PolicyRow({ item, iconVariant }: { item: MarriagePolicyItem; iconVariant: "violet" | "sky" | "mint" }) {
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
      </div>
    </div>
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
            정책만 보여줘요. 청약 가점, 대출 금리 데이터는 포함하지 않습니다.
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
        <div className="mt-6 grid gap-8">
          <div>
            <SectionLabel>혼인신고 후에만 자격됨 ({result.married_only.length})</SectionLabel>
            {result.married_only.length === 0 ? (
              <p className="text-[13px] font-bold text-slate-400">해당하는 정책이 없어요.</p>
            ) : (
              <div className="grid gap-3">
                {result.married_only.map((item) => (
                  <PolicyRow key={item.policy_key} item={item} iconVariant="violet" />
                ))}
              </div>
            )}
          </div>
          <div>
            <SectionLabel>미혼일 때만 자격됨 ({result.unmarried_only.length})</SectionLabel>
            {result.unmarried_only.length === 0 ? (
              <p className="text-[13px] font-bold text-slate-400">해당하는 정책이 없어요.</p>
            ) : (
              <div className="grid gap-3">
                {result.unmarried_only.map((item) => (
                  <PolicyRow key={item.policy_key} item={item} iconVariant="sky" />
                ))}
              </div>
            )}
          </div>
          <div>
            <SectionLabel>
              <span className="inline-flex items-center gap-2">
                <Users size={15} /> 둘 다 해당 ({result.both.length})
              </span>
            </SectionLabel>
            {result.both.length === 0 ? (
              <p className="text-[13px] font-bold text-slate-400">해당하는 정책이 없어요.</p>
            ) : (
              <div className="grid gap-3">
                {result.both.map((item) => (
                  <PolicyRow key={item.policy_key} item={item} iconVariant="mint" />
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
