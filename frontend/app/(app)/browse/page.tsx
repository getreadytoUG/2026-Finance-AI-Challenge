"use client";

import { useEffect, useState } from "react";
import { FaBookOpen } from "react-icons/fa6";
import { browsePolicies, getPolicyCategories } from "@/lib/api";
import type { PolicyBrowseItem, PolicyCategory } from "@/lib/api";
import Pagination from "@/components/Pagination";
import PolicyDetailLink from "@/components/PolicyDetailLink";
import { REGIONS } from "@/lib/profileOptions";

const PAGE_SIZE = 10;

const STATUS_COLORS: Record<string, string> = {
  임박: "var(--accent)",
  여유: "var(--success)",
  상시: "var(--primary)",
  예정: "var(--text-muted)",
  만료: "var(--danger)",
};

function StatusDot({ status }: { status: string }) {
  return (
    <span
      style={{
        display: "inline-block",
        width: 10,
        height: 10,
        borderRadius: "50%",
        background: STATUS_COLORS[status] ?? "var(--text-muted)",
        marginRight: 6,
      }}
    />
  );
}

export default function BrowsePage() {
  const [categories, setCategories] = useState<PolicyCategory[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null);
  const [items, setItems] = useState<PolicyBrowseItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [includeClosed, setIncludeClosed] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("token") ?? "";
    getPolicyCategories(token, { region: selectedRegion ?? undefined, includeClosed })
      .then((res) => setCategories(res.categories))
      .catch(() => {});
  }, [selectedRegion, includeClosed]);

  useEffect(() => {
    const token = localStorage.getItem("token") ?? "";
    setLoading(true);
    setError(null);
    browsePolicies(token, {
      category: selectedCategory ?? undefined,
      region: selectedRegion ?? undefined,
      page,
      pageSize: PAGE_SIZE,
      includeClosed,
    })
      .then((res) => {
        setItems(res.items);
        setTotal(res.total);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "정책을 불러오지 못했습니다."))
      .finally(() => setLoading(false));
  }, [selectedCategory, selectedRegion, page, includeClosed]);

  function handleSelectCategory(name: string | null) {
    setSelectedCategory(name);
    setPage(1);
  }

  function handleSelectRegion(name: string | null) {
    setSelectedRegion(name);
    setPage(1);
  }

  function handleToggleIncludeClosed() {
    setIncludeClosed((v) => !v);
    setPage(1);
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <>
      <div className="page-header">
        <h1>
          <span className="icon-box">
            <FaBookOpen />
          </span>
          정책 읽기
        </h1>
        <p>조건 입력 없이 전체 정책을 카테고리별로 둘러보세요.</p>
      </div>

      <span className="field-label" style={{ display: "block" }}>
        지역
      </span>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 20 }}>
        <button
          className="btn-ghost"
          onClick={() => handleSelectRegion(null)}
          style={{
            borderRadius: 999,
            background: selectedRegion === null ? "var(--primary-tint)" : undefined,
            color: selectedRegion === null ? "var(--primary)" : undefined,
          }}
        >
          전체
        </button>
        {REGIONS.map((r) => (
          <button
            key={r}
            className="btn-ghost"
            onClick={() => handleSelectRegion(r)}
            style={{
              borderRadius: 999,
              background: selectedRegion === r ? "var(--primary-tint)" : undefined,
              color: selectedRegion === r ? "var(--primary)" : undefined,
            }}
          >
            {r}
          </button>
        ))}
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 20 }}>
        <button
          className="btn-ghost"
          onClick={() => handleSelectCategory(null)}
          style={{
            borderRadius: 999,
            background: selectedCategory === null ? "var(--primary-tint)" : undefined,
            color: selectedCategory === null ? "var(--primary)" : undefined,
          }}
        >
          전체
        </button>
        {categories.map((c) => (
          <button
            key={c.name}
            className="btn-ghost"
            onClick={() => handleSelectCategory(c.name)}
            style={{
              borderRadius: 999,
              background: selectedCategory === c.name ? "var(--primary-tint)" : undefined,
              color: selectedCategory === c.name ? "var(--primary)" : undefined,
            }}
          >
            {c.name} ({c.count})
          </button>
        ))}
      </div>

      <label className="checkbox-field">
        <input type="checkbox" checked={includeClosed} onChange={handleToggleIncludeClosed} />
        마감된 정책도 보기
      </label>

      {error && <p className="error-text">{error}</p>}
      {loading && <p>불러오는 중...</p>}
      {!loading && items.length === 0 && !error && <p className="error-text">해당하는 정책이 없습니다.</p>}

      <div className="result-list">
        {items.map((item, i) => (
          <div key={i} className="result-item">
            <div className="result-item-title">
              <StatusDot status={item.status} />
              {item.policy_name}
            </div>
            <div className="result-item-row">
              <span>분야</span>
              <span>{item.large_category}</span>
            </div>
            <div className="result-item-row">
              <span>상태</span>
              <span style={{ display: "inline-flex", alignItems: "center" }}>
                <StatusDot status={item.status} />
                {item.status}
              </span>
            </div>
            <div className="result-item-row">
              <span>신청 기간</span>
              <span>{item.application_period}</span>
            </div>
            <div style={{ marginTop: 12 }}>
              <PolicyDetailLink url={item.reference_url} />
            </div>
          </div>
        ))}
      </div>

      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
    </>
  );
}
