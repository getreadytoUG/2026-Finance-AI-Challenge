"use client";

import { POLICY_CATEGORY_OPTIONS, REGIONS } from "@/lib/profileOptions";
import type { PolicyStatus } from "@/lib/api";
import type { AiPolicySearchState } from "@/lib/useAiPolicySearch";

// 채팅으로 조건을 "말해야만" 검색결과가 바뀌는 게 답답하다는 사용자 피드백(2026-09-02,
// "자소설닷컴처럼 클릭해서 필터할 수 있게")으로 추가한, 대화 없이 바로 클릭/선택으로
// 조건을 바꾸는 드롭다운 바. 챗봇 필터(useAiPolicySearch.filters)와 상태를 완전히
// 공유한다 — 여기서 바꾸면 챗봇 위 필터 칩에도 그대로 반영되고, 반대로 챗봇이 조건을
// 바꾸면 이 드롭다운 값도 같이 바뀐다(둘 다 같은 filters state를 읽고 쓰기 때문).
const STATUS_OPTIONS: { value: PolicyStatus; label: string }[] = [
  { value: "임박", label: "마감임박" },
  { value: "여유", label: "여유" },
  { value: "상시", label: "상시모집" },
  { value: "예정", label: "예정" },
  { value: "만료", label: "마감됨" },
];

function FilterSelect({
  value,
  placeholder,
  options,
  onChange,
  compact,
}: {
  value: string;
  placeholder: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
  compact?: boolean;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={`h-9 rounded-lg border bg-white font-bold outline-none transition ${
        compact ? "px-2 text-[11px]" : "px-2.5 text-[12px]"
      } ${value ? "border-[#2457d6] text-[#2457d6]" : "border-slate-200 text-slate-500"}`}
    >
      <option value="">{placeholder}</option>
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

export default function AiSearchFilterBar({ state, compact = false }: { state: AiPolicySearchState; compact?: boolean }) {
  const { filters, handleSetFilters } = state;
  if (!filters) return null;

  const maritalValue = filters.is_married == null ? "" : filters.is_married ? "married" : "single";

  return (
    <div className="mb-3 flex flex-wrap gap-1.5">
      <FilterSelect
        value={filters.region ?? ""}
        placeholder="지역 전체"
        options={REGIONS.map((r) => ({ value: r, label: r }))}
        onChange={(v) => handleSetFilters({ region: v || null })}
        compact={compact}
      />
      <FilterSelect
        value={maritalValue}
        placeholder="혼인여부 전체"
        options={[
          { value: "single", label: "미혼" },
          { value: "married", label: "기혼" },
        ]}
        onChange={(v) => handleSetFilters({ is_married: v === "" ? null : v === "married" })}
        compact={compact}
      />
      <FilterSelect
        value={filters.category ?? ""}
        placeholder="카테고리 전체"
        options={POLICY_CATEGORY_OPTIONS.map((c) => ({ value: c, label: c }))}
        onChange={(v) => handleSetFilters({ category: v || null })}
        compact={compact}
      />
      <FilterSelect
        value={filters.status ?? ""}
        placeholder="마감상태 전체"
        options={STATUS_OPTIONS}
        onChange={(v) => handleSetFilters({ status: (v || null) as PolicyStatus | null })}
        compact={compact}
      />
    </div>
  );
}
