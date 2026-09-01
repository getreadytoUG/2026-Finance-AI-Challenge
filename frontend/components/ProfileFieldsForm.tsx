"use client";

import { useState } from "react";
import { OCCUPATION_OPTIONS, REGIONS, krwToManwon, manwonToKrw, type OccupationType } from "@/lib/profileOptions";
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
  const [isMarried, setIsMarried] = useState(initial?.is_married ?? false);
  const [spouseAge, setSpouseAge] = useState(initial?.spouse_age != null ? String(initial.spouse_age) : "");
  const [spouseIncome, setSpouseIncome] = useState(
    initial?.spouse_annual_income_krw != null ? String(krwToManwon(initial.spouse_annual_income_krw)) : ""
  );
  const [spouseOccupation, setSpouseOccupation] = useState<OccupationType | "">(initial?.spouse_occupation ?? "");
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
        is_married: isMarried,
        annual_income_krw: manwonToKrw(Number(income)),
        region,
        occupation,
        spouse_age: isMarried && spouseAge ? Number(spouseAge) : null,
        spouse_annual_income_krw: isMarried && spouseIncome ? manwonToKrw(Number(spouseIncome)) : null,
        spouse_occupation: isMarried && spouseOccupation ? spouseOccupation : null,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "저장에 실패했습니다.");
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-5">
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
          나이
          <input
            type="number"
            min={0}
            placeholder="29"
            value={age}
            onChange={(e) => setAge(e.target.value)}
            required
            className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
          />
        </label>
        <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
          연소득 (만원)
          <input
            type="number"
            min={0}
            placeholder="4000"
            value={income}
            onChange={(e) => setIncome(e.target.value)}
            required
            className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
          />
        </label>
      </div>

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
        <div className="mb-2 text-[12px] font-extrabold text-slate-700">지역</div>
        <div className="flex flex-wrap gap-2">
          {REGIONS.map((r) => (
            <button key={r} type="button" className={pillClass(region === r)} onClick={() => setRegion(r)}>
              {r}
            </button>
          ))}
        </div>
      </div>

      <label className="flex items-center gap-2 text-[13px] font-bold text-slate-700">
        <input type="checkbox" checked={isMarried} onChange={(e) => setIsMarried(e.target.checked)} className="h-4 w-4 accent-[#2457d6]" />
        기혼
      </label>

      {isMarried && (
        <div className="rounded-xl bg-[#f5f8fd] p-4">
          <p className="mb-3 text-[12px] font-bold text-slate-500">배우자 정보 (선택)</p>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
              배우자 나이
              <input
                type="number"
                min={0}
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
