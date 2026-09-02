"use client";

import { useState } from "react";
import {
  EMPLOYMENT_TYPE_OPTIONS,
  HOUSING_STATUS_OPTIONS,
  MARITAL_STATUS_OPTIONS,
  OCCUPATION_OPTIONS,
  REGIONS,
  krwToManwon,
  manwonToKrw,
  type EmploymentType,
  type HousingStatusType,
  type MaritalStatusType,
  type OccupationType,
} from "@/lib/profileOptions";
import type { ProfileInput, UserProfile } from "@/lib/api";

// 회원가입 폼의 프로필 입력 부분과 동일한 필드 묶음. 온보딩(소셜 로그인 후
// 프로필 완성) 화면에서 재사용한다. 이메일/비밀번호는 이 컴포넌트가 다루지 않는다.

function pillClass(active: boolean) {
  return `rounded-lg px-3.5 py-2 text-[11px] font-extrabold transition ${
    active ? "bg-[#2457d6] text-white" : "bg-[#eef3f9] text-slate-500 hover:bg-[#e3eaf6]"
  }`;
}

type Props = {
  initial?: UserProfile | null;
  submitLabel: string;
  submittingLabel: string;
  onSubmit: (profile: ProfileInput) => Promise<void>;
};

export default function ProfileFieldsForm({ initial, submitLabel, submittingLabel, onSubmit }: Props) {
  const [age, setAge] = useState(initial?.age != null ? String(initial.age) : "");
  const [income, setIncome] = useState(
    initial?.annual_income_krw != null ? String(krwToManwon(initial.annual_income_krw)) : ""
  );
  const [occupation, setOccupation] = useState<OccupationType | "">(initial?.occupation ?? "");
  const [region, setRegion] = useState<string | null>(initial?.region ?? null);
  const [spouseAge, setSpouseAge] = useState(initial?.spouse_age != null ? String(initial.spouse_age) : "");
  const [spouseIncome, setSpouseIncome] = useState(
    initial?.spouse_annual_income_krw != null ? String(krwToManwon(initial.spouse_annual_income_krw)) : ""
  );
  const [spouseOccupation, setSpouseOccupation] = useState<OccupationType | "">(initial?.spouse_occupation ?? "");

  // 2026-09-01 UPGRADE.md 반영: 확장 프로필 필드. 전부 선택 입력.
  const [maritalStatus, setMaritalStatus] = useState<MaritalStatusType | "">(initial?.marital_status ?? "");
  const [marriageYears, setMarriageYears] = useState(initial?.marriage_years != null ? String(initial.marriage_years) : "");
  const [childrenCount, setChildrenCount] = useState(initial?.children_count != null ? String(initial.children_count) : "");
  const [isPregnant, setIsPregnant] = useState(initial?.is_pregnant ?? false);
  const [desiredRegion, setDesiredRegion] = useState<string | null>(initial?.desired_region ?? null);
  const [employmentType, setEmploymentType] = useState<EmploymentType | "">(initial?.employment_type ?? "");
  const [isSmeEmployee, setIsSmeEmployee] = useState(initial?.is_sme_employee ?? false);
  const [housingStatus, setHousingStatus] = useState<HousingStatusType | "">(initial?.housing_status ?? "");
  const [netWorth, setNetWorth] = useState(initial?.net_worth_krw != null ? String(krwToManwon(initial.net_worth_krw)) : "");
  const [monthlySavings, setMonthlySavings] = useState(
    initial?.monthly_savings_capacity_krw != null ? String(krwToManwon(initial.monthly_savings_capacity_krw)) : ""
  );
  // 2026-09-02 추가: 장애인/국가보훈대상자 전용 정책이 있어 수집(선택 입력).
  const [hasDisability, setHasDisability] = useState(initial?.has_disability ?? false);
  const [isVeteran, setIsVeteran] = useState(initial?.is_veteran ?? false);
  const isMarried = maritalStatus === "engaged" || maritalStatus === "newlywed";

  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const canSubmit = Boolean(age && income && occupation && region);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!region || !occupation) return;
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit({
        age: Number(age),
        is_married: maritalStatus === "newlywed",
        annual_income_krw: manwonToKrw(Number(income)),
        region,
        occupation,
        spouse_age: isMarried && spouseAge ? Number(spouseAge) : null,
        spouse_annual_income_krw: isMarried && spouseIncome ? manwonToKrw(Number(spouseIncome)) : null,
        spouse_occupation: isMarried && spouseOccupation ? spouseOccupation : null,
        marital_status: maritalStatus || null,
        marriage_years: maritalStatus === "newlywed" && marriageYears ? Number(marriageYears) : null,
        children_count: childrenCount ? Number(childrenCount) : null,
        is_pregnant: isPregnant,
        desired_region: desiredRegion,
        employment_type: employmentType || null,
        is_sme_employee: isSmeEmployee,
        housing_status: housingStatus || null,
        net_worth_krw: netWorth ? manwonToKrw(Number(netWorth)) : null,
        monthly_savings_capacity_krw: monthlySavings ? manwonToKrw(Number(monthlySavings)) : null,
        has_disability: hasDisability,
        is_veteran: isVeteran,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "저장에 실패했습니다.");
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-5">
      {/* 기본 인적사항 */}
      <div className="text-[11px] font-extrabold uppercase tracking-[.1em] text-slate-400">기본 인적사항</div>
      <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
        나이
        <input
          type="number"
          min={0}
          max={130}
          placeholder="29"
          value={age}
          onChange={(e) => setAge(e.target.value)}
          required
          className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
        />
        {/* 2026-09-02 QA: min/max만 걸어두면 브라우저 네이티브 툴팁 외엔 안내가
            없어서 왜 제출이 안 되는지 헷갈릴 수 있었다 — 상시 노출 힌트로 보강. */}
        <span className="text-[11px] font-semibold text-slate-400">0~130세 사이로 입력해주세요.</span>
      </label>

      <div>
        <div className="mb-2 text-[12px] font-extrabold text-slate-700">혼인 여부</div>
        <div className="flex flex-wrap gap-2">
          {MARITAL_STATUS_OPTIONS.map((o) => (
            <button key={o.value} type="button" className={pillClass(maritalStatus === o.value)} onClick={() => setMaritalStatus(o.value)}>
              {o.label}
            </button>
          ))}
        </div>
        {maritalStatus === "newlywed" && (
          <input
            type="number"
            min={0}
            max={100}
            placeholder="신혼 몇 년차인가요? (예: 1)"
            value={marriageYears}
            onChange={(e) => setMarriageYears(e.target.value)}
            className="mt-2 h-11 w-full rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6]"
          />
        )}
      </div>

      {isMarried && (
        <div className="rounded-xl bg-[#f5f8fd] p-4">
          <p className="mb-3 text-[12px] font-bold text-slate-500">배우자 정보 (선택)</p>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
              배우자 나이
              <input
                type="number"
                min={0}
                max={130}
                value={spouseAge}
                onChange={(e) => setSpouseAge(e.target.value)}
                className="h-11 rounded-xl border border-slate-200 bg-white px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6]"
              />
            </label>
            <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
              배우자 연소득 (만원)
              <input
                type="number"
                min={0}
                max={200000}
                value={spouseIncome}
                onChange={(e) => setSpouseIncome(e.target.value)}
                className="h-11 rounded-xl border border-slate-200 bg-white px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6]"
              />
            </label>
          </div>
          <div className="mt-3 text-[12px] font-extrabold text-slate-700">배우자 직업 구분</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {OCCUPATION_OPTIONS.map((o) => (
              <button
                key={o.value}
                type="button"
                className={pillClass(spouseOccupation === o.value)}
                onClick={() => setSpouseOccupation(o.value)}
              >
                {o.label}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
          자녀 수
          <input
            type="number"
            min={0}
            max={20}
            placeholder="0"
            value={childrenCount}
            onChange={(e) => setChildrenCount(e.target.value)}
            className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
          />
        </label>
        <label className="flex items-center gap-2 self-end pb-1 text-[13px] font-bold text-slate-700">
          <input type="checkbox" checked={isPregnant} onChange={(e) => setIsPregnant(e.target.checked)} className="h-4 w-4 accent-[#2457d6]" />
          임신 중이에요
        </label>
      </div>

      <div className="flex flex-wrap gap-x-6 gap-y-2">
        <label className="flex items-center gap-2 text-[13px] font-bold text-slate-700">
          <input
            type="checkbox"
            checked={hasDisability}
            onChange={(e) => setHasDisability(e.target.checked)}
            className="h-4 w-4 accent-[#2457d6]"
          />
          장애가 있어요
        </label>
        <label className="flex items-center gap-2 text-[13px] font-bold text-slate-700">
          <input type="checkbox" checked={isVeteran} onChange={(e) => setIsVeteran(e.target.checked)} className="h-4 w-4 accent-[#2457d6]" />
          국가보훈대상자예요
        </label>
      </div>

      <div>
        <div className="mb-2 text-[12px] font-extrabold text-slate-700">거주 지역</div>
        <div className="flex flex-wrap gap-2">
          {REGIONS.map((r) => (
            <button key={r} type="button" className={pillClass(region === r)} onClick={() => setRegion(r)}>
              {r}
            </button>
          ))}
        </div>
      </div>

      <div>
        <div className="mb-2 text-[12px] font-extrabold text-slate-700">희망 지역 (선택, 거주 지역과 다를 경우)</div>
        <div className="flex flex-wrap gap-2">
          {REGIONS.map((r) => (
            <button key={r} type="button" className={pillClass(desiredRegion === r)} onClick={() => setDesiredRegion(desiredRegion === r ? null : r)}>
              {r}
            </button>
          ))}
        </div>
      </div>

      {/* 소득 및 직업 */}
      <div className="border-t border-slate-100 pt-5 text-[11px] font-extrabold uppercase tracking-[.1em] text-slate-400">소득 및 직업</div>
      <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
        연소득 (만원)
        <input
          type="number"
          min={0}
          max={200000}
          placeholder="4000"
          value={income}
          onChange={(e) => setIncome(e.target.value)}
          required
          className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
        />
      </label>

      <div>
        <div className="mb-2 text-[12px] font-extrabold text-slate-700">직업 구분</div>
        <div className="flex flex-wrap gap-2">
          {OCCUPATION_OPTIONS.map((o) => (
            <button key={o.value} type="button" className={pillClass(occupation === o.value)} onClick={() => setOccupation(o.value)}>
              {o.label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <div className="mb-2 text-[12px] font-extrabold text-slate-700">근로 형태 (선택)</div>
        <div className="flex flex-wrap gap-2">
          {EMPLOYMENT_TYPE_OPTIONS.map((o) => (
            <button
              key={o.value}
              type="button"
              className={pillClass(employmentType === o.value)}
              onClick={() => setEmploymentType(employmentType === o.value ? "" : o.value)}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>

      <label className="flex items-center gap-2 text-[13px] font-bold text-slate-700">
        <input type="checkbox" checked={isSmeEmployee} onChange={(e) => setIsSmeEmployee(e.target.checked)} className="h-4 w-4 accent-[#2457d6]" />
        중소기업 재직 중이에요
      </label>

      {/* 자산 및 주거 */}
      <div className="border-t border-slate-100 pt-5 text-[11px] font-extrabold uppercase tracking-[.1em] text-slate-400">자산 및 주거</div>
      <div>
        <div className="mb-2 text-[12px] font-extrabold text-slate-700">무주택 여부 (선택)</div>
        <div className="flex flex-wrap gap-2">
          {HOUSING_STATUS_OPTIONS.map((o) => (
            <button
              key={o.value}
              type="button"
              className={pillClass(housingStatus === o.value)}
              onClick={() => setHousingStatus(housingStatus === o.value ? "" : o.value)}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
          순자산 (만원, 선택)
          <input
            type="number"
            min={0}
            max={200000}
            placeholder="부동산·금융자산 합산"
            value={netWorth}
            onChange={(e) => setNetWorth(e.target.value)}
            className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
          />
        </label>
        <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
          월 저축 가능 여력 (만원, 선택)
          <input
            type="number"
            min={0}
            max={200000}
            value={monthlySavings}
            onChange={(e) => setMonthlySavings(e.target.value)}
            className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
          />
        </label>
      </div>

      {error && <p className="text-[12px] font-bold text-rose-500">{error}</p>}
      <button
        type="submit"
        disabled={submitting || !canSubmit}
        className="mt-1 flex h-12 items-center justify-center gap-2 rounded-xl bg-[#2457d6] text-[13px] font-extrabold text-white shadow-[0_12px_22px_rgba(36,87,214,.2)] transition hover:-translate-y-0.5 hover:bg-[#1949c1] disabled:opacity-50"
      >
        {submitting ? submittingLabel : submitLabel}
      </button>
    </form>
  );
}
