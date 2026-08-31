"use client";

import { useEffect, useMemo, useState } from "react";
import { Check, Search, SlidersHorizontal } from "lucide-react";
import { DashboardLayout, SectionLabel } from "@/components/DashboardLayout";
import Pagination from "@/components/Pagination";
import PolicyDetailLink from "@/components/PolicyDetailLink";
import StatusPill from "@/components/StatusPill";
import MarriageComparisonTab from "./MarriageComparisonTab";
import {
  browsePolicies,
  callTool,
  getMe,
  getPolicyCategories,
  getRegions,
  type PolicyBrowseItem,
  type PolicyCategory,
} from "@/lib/api";
import { krwToManwon, manwonToKrw } from "@/lib/profileOptions";

const PAGE_SIZE = 10;

type PolicyOption = {
  policy_name: string;
  benefit_description: string;
  application_period: string;
  reference_url: string;
  is_newlywed_policy: boolean;
};

type PolicyMatchOutput = {
  options: PolicyOption[];
};

function MatchTab() {
  const [regions, setRegions] = useState<string[]>([]);
  const [age, setAge] = useState("29");
  const [isMarried, setIsMarried] = useState(false);
  const [income, setIncome] = useState("4000");
  const [spouseIncome, setSpouseIncome] = useState("");
  const [region, setRegion] = useState<string | null>(null);
  const [result, setResult] = useState<PolicyMatchOutput | null>(null);
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("token") ?? "";
    getRegions(token)
      .then((res) => setRegions(res.regions))
      .catch(() => {});
    getMe(token)
      .then((me) => {
        if (me.age != null) setAge(String(me.age));
        if (me.is_married != null) setIsMarried(me.is_married);
        if (me.annual_income_krw != null) setIncome(String(krwToManwon(me.annual_income_krw)));
        if (me.region != null) setRegion(me.region);
        if (me.spouse_annual_income_krw != null) setSpouseIncome(String(krwToManwon(me.spouse_annual_income_krw)));
      })
      .catch(() => {});
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!region) return;
    setError(null);
    setResult(null);
    setPage(1);
    setLoading(true);
    const token = localStorage.getItem("token") ?? "";
    try {
      const output = await callTool<PolicyMatchOutput>(token, "policy_matcher", {
        age: Number(age),
        is_married: isMarried,
        annual_income_krw: manwonToKrw(Number(income)),
        spouse_annual_income_krw: isMarried && spouseIncome ? manwonToKrw(Number(spouseIncome)) : null,
        region,
      });
      setResult(output);
    } catch (err) {
      setError(err instanceof Error ? err.message : "요청이 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }

  const totalPages = result ? Math.max(1, Math.ceil(result.options.length / PAGE_SIZE)) : 1;
  const pageOptions = result ? result.options.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE) : [];

  return (
    <div>
      <div className="rounded-[22px] border border-slate-200/80 bg-white p-6">
        <form onSubmit={handleSubmit} className="grid gap-4 sm:grid-cols-2">
          <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
            나이
            <input
              type="number"
              value={age}
              onChange={(e) => setAge(e.target.value)}
              className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
            />
          </label>
          <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
            연소득 (만원)
            <input
              type="number"
              value={income}
              onChange={(e) => setIncome(e.target.value)}
              className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
            />
          </label>
          <label className="flex items-center gap-2 text-[13px] font-bold text-slate-700 sm:col-span-2">
            <input type="checkbox" checked={isMarried} onChange={(e) => setIsMarried(e.target.checked)} className="h-4 w-4 accent-[#2457d6]" />
            기혼
          </label>
          {isMarried && (
            <label className="grid gap-2 text-[12px] font-extrabold text-slate-700 sm:col-span-2">
              배우자 연소득 (만원, 선택)
              <input
                type="number"
                value={spouseIncome}
                onChange={(e) => setSpouseIncome(e.target.value)}
                placeholder="입력하면 가구소득(본인+배우자) 합산 기준으로 조회해요"
                className="h-12 rounded-xl border border-slate-200 px-4 text-[13px] font-semibold outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
              />
            </label>
          )}
          <div className="sm:col-span-2">
            <div className="mb-2 text-[12px] font-extrabold text-slate-700">지역</div>
            <div className="flex flex-wrap gap-2">
              {regions.map((r) => (
                <button
                  key={r}
                  type="button"
                  onClick={() => setRegion(r)}
                  className={`rounded-lg px-3.5 py-2 text-[11px] font-extrabold transition ${
                    region === r ? "bg-[#2457d6] text-white" : "bg-[#eef3f9] text-slate-500 hover:bg-[#e3eaf6]"
                  }`}
                >
                  {r}
                </button>
              ))}
            </div>
          </div>
          <button
            type="submit"
            disabled={loading || !region}
            className="h-12 rounded-xl bg-[#2457d6] text-[13px] font-extrabold text-white shadow-[0_10px_20px_rgba(36,87,214,.18)] transition hover:bg-[#1949c1] disabled:opacity-50 sm:col-span-2"
          >
            {loading ? "찾는 중..." : region ? "금융 정책 찾기" : "지역을 선택해주세요"}
          </button>
        </form>
      </div>

      {error && <p className="mt-4 text-[13px] font-bold text-rose-500">{error}</p>}

      {result &&
        (result.options.length === 0 ? (
          <p className="mt-4 text-[13px] font-bold text-slate-400">지금 신청 가능한 금융 정책을 찾지 못했습니다.</p>
        ) : (
          <>
            <div className="mt-6 grid gap-3">
              {pageOptions.map((option, i) => (
                <div key={i} className="flex flex-col gap-4 rounded-2xl border border-slate-200/80 bg-white p-5 sm:flex-row sm:items-center">
                  <span className="policy-list-icon blue">
                    <Search size={19} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      {option.is_newlywed_policy && (
                        <span className="policy-status available">
                          <span />
                          신혼부부
                        </span>
                      )}
                      <span className="text-[15px] font-extrabold tracking-[-.03em] text-ink">{option.policy_name}</span>
                    </div>
                    <p className="mt-2 text-[12px] leading-5 text-slate-500">{option.benefit_description}</p>
                    <div className="mt-2 text-[11px] font-semibold text-slate-400">신청 기간 {option.application_period}</div>
                    <PolicyDetailLink url={option.reference_url} className="mt-2" />
                  </div>
                </div>
              ))}
            </div>
            <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
          </>
        ))}
    </div>
  );
}

function BrowseTab() {
  const [categories, setCategories] = useState<PolicyCategory[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null);
  const [items, setItems] = useState<PolicyBrowseItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [includeClosed, setIncludeClosed] = useState(false);
  const [query, setQuery] = useState("");
  const [regions, setRegions] = useState<string[]>([]);

  useEffect(() => {
    const token = localStorage.getItem("token") ?? "";
    getRegions(token)
      .then((res) => setRegions(res.regions))
      .catch(() => {});
  }, []);

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

  const filteredItems = useMemo(
    () => items.filter((item) => (item.policy_name + item.benefit_description).toLowerCase().includes(query.toLowerCase())),
    [items, query]
  );

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div>
      <div className="mb-6 flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={17} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="정책명, 지원 내용으로 검색 (현재 페이지 안에서)"
            className="h-12 w-full rounded-xl border border-slate-200 bg-white pl-11 pr-4 text-[13px] font-semibold outline-none transition focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
          />
        </div>
        <button
          type="button"
          onClick={() => {
            setIncludeClosed((v) => !v);
            setPage(1);
          }}
          className={`flex h-12 shrink-0 items-center gap-2 rounded-xl border px-4 text-[12px] font-extrabold transition ${
            includeClosed ? "border-[#2457d6] bg-[#eef3ff] text-[#2457d6]" : "border-slate-200 bg-white text-slate-500 hover:border-[#2457d6] hover:text-[#2457d6]"
          }`}
        >
          <SlidersHorizontal size={16} /> 마감된 정책도 보기
        </button>
      </div>

      <div className="mb-3">
        <div className="mb-2 text-[11px] font-extrabold uppercase tracking-[.1em] text-slate-400">지역</div>
        <div className="flex flex-wrap gap-1.5">
          <button
            onClick={() => {
              setSelectedRegion(null);
              setPage(1);
            }}
            className={`shrink-0 rounded-lg px-3.5 py-2 text-[11px] font-extrabold ${selectedRegion === null ? "bg-[#2457d6] text-white" : "bg-[#eef3f9] text-slate-500"}`}
          >
            전체
          </button>
          {regions.map((r) => (
            <button
              key={r}
              onClick={() => {
                setSelectedRegion(r);
                setPage(1);
              }}
              className={`shrink-0 rounded-lg px-3.5 py-2 text-[11px] font-extrabold ${selectedRegion === r ? "bg-[#2457d6] text-white" : "bg-[#eef3f9] text-slate-500"}`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      <div className="mb-6 flex gap-1.5 overflow-x-auto rounded-xl bg-[#eef3f9] p-1">
        <button
          onClick={() => {
            setSelectedCategory(null);
            setPage(1);
          }}
          className={`shrink-0 rounded-lg px-3.5 py-2 text-[11px] font-extrabold ${selectedCategory === null ? "bg-white text-[#2457d6] shadow-sm" : "text-slate-500"}`}
        >
          전체
        </button>
        {categories.map((c) => (
          <button
            key={c.name}
            onClick={() => {
              setSelectedCategory(c.name);
              setPage(1);
            }}
            className={`shrink-0 rounded-lg px-3.5 py-2 text-[11px] font-extrabold ${selectedCategory === c.name ? "bg-white text-[#2457d6] shadow-sm" : "text-slate-500"}`}
          >
            {c.name} ({c.count})
          </button>
        ))}
      </div>

      <SectionLabel>{loading ? "불러오는 중..." : `정책 ${filteredItems.length}개`}</SectionLabel>

      {error && <p className="text-[13px] font-bold text-rose-500">{error}</p>}
      {!loading && filteredItems.length === 0 && !error && (
        <div className="rounded-2xl border border-dashed border-slate-300 p-12 text-center text-[13px] font-bold text-slate-400">
          조건에 맞는 정책이 없어요. 다른 조건으로 찾아보세요.
        </div>
      )}

      <div className="grid gap-3">
        {filteredItems.map((item, i) => (
          <div
            key={i}
            className="group flex flex-col gap-4 rounded-2xl border border-slate-200/80 bg-white p-5 transition hover:-translate-y-0.5 hover:border-[#cddafb] hover:shadow-[0_14px_30px_rgba(28,50,88,.07)] sm:flex-row sm:items-center"
          >
            <span className="policy-list-icon sky">
              <Check size={18} />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-[15px] font-extrabold tracking-[-.03em] text-ink">{item.policy_name}</span>
                <StatusPill status={item.status} />
              </div>
              <div className="mt-1.5 text-[11px] font-semibold text-slate-400">{item.large_category}</div>
              <p className="mt-2 text-[12px] leading-5 text-slate-500">{item.benefit_description}</p>
              <div className="mt-2 text-[11px] font-semibold text-slate-400">신청 기간 {item.application_period}</div>
            </div>
            <PolicyDetailLink url={item.reference_url} className="shrink-0" />
          </div>
        ))}
      </div>

      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
    </div>
  );
}

export default function PolicyPage() {
  const [tab, setTab] = useState<"match" | "browse" | "marriage">("match");

  return (
    <DashboardLayout eyebrow="POLICY MATCHING" title="정책 매칭">
      <div className="mb-6 inline-flex gap-1.5 rounded-xl bg-[#eef3f9] p-1">
        <button
          onClick={() => setTab("match")}
          className={`rounded-lg px-4 py-2.5 text-[12px] font-extrabold transition ${tab === "match" ? "bg-white text-[#2457d6] shadow-sm" : "text-slate-500"}`}
        >
          맞춤 매칭
        </button>
        <button
          onClick={() => setTab("browse")}
          className={`rounded-lg px-4 py-2.5 text-[12px] font-extrabold transition ${tab === "browse" ? "bg-white text-[#2457d6] shadow-sm" : "text-slate-500"}`}
        >
          전체 탐색
        </button>
        <button
          onClick={() => setTab("marriage")}
          className={`rounded-lg px-4 py-2.5 text-[12px] font-extrabold transition ${tab === "marriage" ? "bg-white text-[#2457d6] shadow-sm" : "text-slate-500"}`}
        >
          혼인신고 비교
        </button>
      </div>
      {tab === "match" ? <MatchTab /> : tab === "browse" ? <BrowseTab /> : <MarriageComparisonTab />}
    </DashboardLayout>
  );
}
