"use client";

import { useState } from "react";

export const OCCUPATION_LABELS: Record<string, string> = {
  student: "학생",
  employee: "직장인",
  self_employed: "자영업",
  unemployed: "무직",
  other: "기타",
};

export function formatDateTime(value: string | null): string {
  if (!value) return "-";
  return new Date(value).toLocaleString("ko-KR");
}

const TONE_ORB: Record<string, string> = {
  blue: "bg-[#edf3ff]",
  mint: "bg-[#e8f8f4]",
  violet: "bg-[#f0eeff]",
};

export function KpiCard({ label, value, tone = "blue" }: { label: string; value: string | number; tone?: "blue" | "mint" | "violet" }) {
  return (
    <div className="relative overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-5">
      <div className={`absolute -right-[22px] -top-7 h-[108px] w-[108px] rounded-full opacity-90 ${TONE_ORB[tone]}`} />
      <div className="relative">
        <div className="text-[11px] font-bold text-slate-400">{label}</div>
        <div className="mt-3 text-[24px] font-extrabold tracking-[-.05em] text-ink">{value}</div>
      </div>
    </div>
  );
}

export function ExpandableCell({ text, maxLength = 40 }: { text: string; maxLength?: number }) {
  const [expanded, setExpanded] = useState(false);

  if (!text) return <span>-</span>;
  if (text.length <= maxLength) return <span>{text}</span>;

  // 지역코드처럼 콤마로만 구분되고 공백이 없는 문자열은 자연스러운 줄바꿈 지점이
  // 없어서 word-break: break-word를 쓰면 숫자 중간이 잘린다 — 콤마 뒤에 공백을
  // 넣어 그 지점에서 줄바꿈되게 한다(표시용 변환일 뿐 실제 값은 그대로 전달됨).
  const wrappable = text.replace(/,/g, ", ");

  return (
    <div className={`max-w-[320px] ${expanded ? "whitespace-normal" : "whitespace-nowrap"}`}>
      {expanded ? wrappable : `${text.slice(0, maxLength)}…`}{" "}
      <button
        type="button"
        className="whitespace-nowrap border-none bg-transparent p-0 text-[12px] font-bold text-[#2457d6] hover:underline"
        onClick={() => setExpanded((prev) => !prev)}
      >
        {expanded ? "접기" : "더보기"}
      </button>
    </div>
  );
}

export function BarRow({ label, count, max }: { label: string; count: number; max: number }) {
  const pct = max > 0 ? Math.round((count / max) * 100) : 0;
  return (
    <div className="mb-2.5 flex items-center gap-2.5 text-[13px]">
      <span className="w-[110px] shrink-0 text-slate-500">{label}</span>
      <span className="h-2.5 flex-1 overflow-hidden rounded-full bg-[#f0f4f9]">
        <span className="block h-full rounded-full bg-[#2457d6]" style={{ width: `${pct}%` }} />
      </span>
      <span className="w-10 shrink-0 text-right font-bold text-ink">{count}</span>
    </div>
  );
}
