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
