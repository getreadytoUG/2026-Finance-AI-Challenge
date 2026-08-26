"use client";

import { useEffect, useState } from "react";
import { getAdminPolicyStats, refreshAdminPolicyCache, type AdminPolicyStatsResponse } from "@/lib/api";
import AdminGuard from "@/components/AdminGuard";
import { BarRow, formatDateTime } from "@/components/AdminWidgets";

function PoliciesContent() {
  const [stats, setStats] = useState<AdminPolicyStatsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshMessage, setRefreshMessage] = useState<string | null>(null);

  function load() {
    const token = localStorage.getItem("token") ?? "";
    return getAdminPolicyStats(token)
      .then(setStats)
      .catch((err) => setError(err instanceof Error ? err.message : "불러오지 못했습니다."));
  }

  useEffect(() => {
    load();
  }, []);

  async function handleRefreshCache() {
    setRefreshing(true);
    setRefreshMessage(null);
    try {
      const token = localStorage.getItem("token") ?? "";
      const res = await refreshAdminPolicyCache(token);
      setRefreshMessage(`${res.upserted}건 갱신 완료`);
      await load();
    } catch (err) {
      setRefreshMessage(err instanceof Error ? err.message : "갱신에 실패했습니다.");
    } finally {
      setRefreshing(false);
    }
  }

  const maxCategoryCount = stats ? Math.max(1, ...stats.by_category.map((c) => c.count)) : 1;
  const maxStatusCount = stats ? Math.max(1, ...stats.by_status.map((s) => s.count)) : 1;

  return (
    <div className="card">
      {error && <p className="error-text">{error}</p>}
      {!stats && !error && <p>불러오는 중...</p>}
      {stats && (
        <>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
            <div>
              <div style={{ fontSize: 14, color: "var(--text-muted)" }}>
                총 {stats.total}건 · 마지막 갱신 {formatDateTime(stats.last_refreshed_at)}
              </div>
              <div style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 4 }}>
                링크 없는 정책 {stats.missing_link_count}건 · 전국형(추정) {stats.nationwide_template_count}건
              </div>
            </div>
            <button type="button" className="btn-ghost" onClick={handleRefreshCache} disabled={refreshing}>
              {refreshing ? "갱신 중..." : "지금 갱신"}
            </button>
          </div>
          {refreshMessage && <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 16 }}>{refreshMessage}</p>}

          <div style={{ fontWeight: 700, marginBottom: 12 }}>분야별 분포</div>
          {stats.by_category.map((c) => (
            <BarRow key={c.name} label={c.name} count={c.count} max={maxCategoryCount} />
          ))}

          <div style={{ fontWeight: 700, margin: "24px 0 12px" }}>상태별 분포</div>
          {stats.by_status.map((s) => (
            <BarRow key={s.status} label={s.status} count={s.count} max={maxStatusCount} />
          ))}
        </>
      )}
    </div>
  );
}

export default function AdminPoliciesPage() {
  return (
    <AdminGuard>
      <div className="page-header">
        <h1>🗂️ 정책</h1>
        <p>정책 캐시 데이터 현황을 확인하고 갱신하세요.</p>
      </div>
      <PoliciesContent />
    </AdminGuard>
  );
}
