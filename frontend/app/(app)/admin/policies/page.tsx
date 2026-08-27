"use client";

import { useEffect, useState } from "react";
import { getAdminPolicyStats, refreshAdminPolicyCache, type AdminPolicyStatsResponse } from "@/lib/api";
import AdminGuard from "@/components/AdminGuard";
import { DashboardLayout } from "@/components/DashboardLayout";
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
    <div className="rounded-[22px] border border-slate-200/80 bg-white p-6">
      {error && <p className="text-[13px] font-bold text-rose-500">{error}</p>}
      {!stats && !error && <p className="text-[13px] text-slate-400">불러오는 중...</p>}
      {stats && (
        <>
          <div className="mb-5 flex items-center justify-between">
            <div>
              <div className="text-[14px] font-bold text-slate-500">
                총 {stats.total}건 · 마지막 갱신 {formatDateTime(stats.last_refreshed_at)}
              </div>
              <div className="mt-1 text-[12px] text-slate-400">
                링크 없는 정책 {stats.missing_link_count}건 · 전국형(추정) {stats.nationwide_template_count}건
              </div>
            </div>
            <button
              type="button"
              onClick={handleRefreshCache}
              disabled={refreshing}
              className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-[12px] font-extrabold text-slate-600 transition hover:border-[#2457d6] hover:text-[#2457d6] disabled:opacity-50"
            >
              {refreshing ? "갱신 중..." : "지금 갱신"}
            </button>
          </div>
          {refreshMessage && <p className="mb-4 text-[12px] text-slate-500">{refreshMessage}</p>}

          <div className="mb-3 text-[14px] font-extrabold text-ink">분야별 분포</div>
          {stats.by_category.map((c) => (
            <BarRow key={c.name} label={c.name} count={c.count} max={maxCategoryCount} />
          ))}

          <div className="mb-3 mt-6 text-[14px] font-extrabold text-ink">상태별 분포</div>
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
      <DashboardLayout eyebrow="ADMIN" title="정책">
        <PoliciesContent />
      </DashboardLayout>
    </AdminGuard>
  );
}
