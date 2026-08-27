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

export function KpiCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="admin-kpi-card">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
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
    <div style={{ whiteSpace: expanded ? "normal" : "nowrap", maxWidth: 320 }}>
      {expanded ? wrappable : `${text.slice(0, maxLength)}…`}{" "}
      <button
        type="button"
        className="link"
        style={{ fontSize: 12, whiteSpace: "nowrap", background: "none", border: "none", padding: 0, cursor: "pointer" }}
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
    <div className="admin-bar-row">
      <span className="admin-bar-label">{label}</span>
      <span className="admin-bar-track">
        <span className="admin-bar-fill" style={{ width: `${pct}%` }} />
      </span>
      <span className="admin-bar-count">{count}</span>
    </div>
  );
}
