"use client";

import { useEffect, useState } from "react";
import { getAdminPolicyList, getPolicyCategories, type AdminPolicyItem, type PolicyCategory } from "@/lib/api";
import { formatApplicationPeriod } from "@/lib/policyFormat";
import AdminGuard from "@/components/AdminGuard";
import { DashboardLayout } from "@/components/DashboardLayout";
import PolicyDetailLink from "@/components/PolicyDetailLink";
import Pagination from "@/components/Pagination";
import { ExpandableCell, formatDateTime } from "@/components/AdminWidgets";

const PAGE_SIZE = 20;

const STATUS_OPTIONS = ["임박", "여유", "상시", "예정", "만료"];

const TH_CLASS = "px-3 py-2.5 text-left text-[12px] font-bold text-slate-400";
const TD_CLASS = "border-t border-slate-100 px-3 py-2.5 text-[13px] text-ink align-top";

function chipClass(active: boolean) {
  return `rounded-full px-3 py-1.5 text-[12px] font-bold transition ${
    active ? "border border-[#2457d6] bg-[#eef3ff] text-[#2457d6]" : "border border-slate-200 bg-white text-slate-500 hover:border-[#2457d6] hover:text-[#2457d6]"
  }`;
}

function PoliciesListContent() {
  const [categories, setCategories] = useState<PolicyCategory[]>([]);
  const [keywordInput, setKeywordInput] = useState("");
  const [keyword, setKeyword] = useState("");
  const [category, setCategory] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  const [items, setItems] = useState<AdminPolicyItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("token") ?? "";
    getPolicyCategories(token)
      .then((res) => setCategories(res.categories))
      .catch(() => {});
  }, []);

  function load(nextPage: number, nextKeyword: string, nextCategory: string | null, nextStatus: string | null) {
    setLoading(true);
    setError(null);
    const token = localStorage.getItem("token") ?? "";
    getAdminPolicyList(token, {
      keyword: nextKeyword || undefined,
      category: nextCategory ?? undefined,
      status: nextStatus ?? undefined,
      page: nextPage,
      pageSize: PAGE_SIZE,
    })
      .then((res) => {
        setItems(res.items);
        setTotal(res.total);
        setPage(res.page);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "불러오지 못했습니다."))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load(1, keyword, category, status);
  }, [keyword, category, status]);

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    setKeyword(keywordInput.trim());
  }

  function handleSelectCategory(name: string) {
    setCategory((prev) => (prev === name ? null : name));
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="rounded-[22px] border border-slate-200/80 bg-white p-6">
      <form onSubmit={handleSearchSubmit} className="mb-4 flex gap-2">
        <input
          placeholder="정책명 검색"
          value={keywordInput}
          onChange={(e) => setKeywordInput(e.target.value)}
          className="h-11 max-w-[280px] flex-1 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
        />
        <button type="submit" className="rounded-xl border border-slate-200 bg-white px-4 text-[12px] font-extrabold text-slate-600 transition hover:border-[#2457d6] hover:text-[#2457d6]">
          검색
        </button>
      </form>

      <div className="mb-2 flex flex-wrap gap-1.5">
        {categories.map((c) => (
          <button key={c.name} type="button" onClick={() => handleSelectCategory(c.name)} className={chipClass(category === c.name)}>
            {c.name} ({c.count})
          </button>
        ))}
      </div>

      <div className="mb-4 flex flex-wrap gap-1.5">
        {STATUS_OPTIONS.map((s) => (
          <button key={s} type="button" onClick={() => setStatus((prev) => (prev === s ? null : s))} className={chipClass(status === s)}>
            {s}
          </button>
        ))}
      </div>

      <div className="mb-3 text-[13px] text-slate-400">총 {total}건</div>

      {error && <p className="text-[13px] font-bold text-rose-500">{error}</p>}
      {loading && <p className="text-[13px] text-slate-400">불러오는 중...</p>}

      {!loading && items.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-[13px]">
            <thead>
              <tr>
                <th className={TH_CLASS}>정책명</th>
                <th className={TH_CLASS}>정책 내용</th>
                <th className={TH_CLASS}>분야</th>
                <th className={TH_CLASS}>상태</th>
                <th className={TH_CLASS}>신청 기간</th>
                <th className={TH_CLASS}>지역 코드</th>
                <th className={TH_CLASS}>링크</th>
                <th className={TH_CLASS}>갱신 시각</th>
              </tr>
            </thead>
            <tbody>
              {items.map((p) => (
                <tr key={p.policy_key}>
                  <td className={`${TD_CLASS} whitespace-nowrap`}>{p.policy_name}</td>
                  <td className={TD_CLASS}>
                    <ExpandableCell text={p.description} maxLength={30} />
                  </td>
                  <td className={`${TD_CLASS} whitespace-nowrap`}>{p.large_category}</td>
                  <td className={`${TD_CLASS} whitespace-nowrap`}>{p.status}</td>
                  <td className={`${TD_CLASS} whitespace-nowrap`}>{formatApplicationPeriod(p.application_period)}</td>
                  <td className={TD_CLASS}>
                    <ExpandableCell text={p.region_code} maxLength={20} />
                  </td>
                  <td className={`${TD_CLASS} whitespace-nowrap`}>
                    <PolicyDetailLink url={p.apply_url} className="text-[12px]" />
                  </td>
                  <td className={`${TD_CLASS} whitespace-nowrap`}>{formatDateTime(p.refreshed_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Pagination page={page} totalPages={totalPages} onPageChange={(next) => load(next, keyword, category, status)} />
    </div>
  );
}

export default function AdminPoliciesListPage() {
  return (
    <AdminGuard>
      <DashboardLayout eyebrow="ADMIN" title="정책 목록">
        <PoliciesListContent />
      </DashboardLayout>
    </AdminGuard>
  );
}
