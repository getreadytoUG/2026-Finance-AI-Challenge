"use client";

import { useEffect, useState } from "react";
import { FaLandmark, FaRing } from "react-icons/fa6";
import { callTool, getMe, getRegions } from "@/lib/api";
import Pagination from "@/components/Pagination";
import PolicyDetailLink from "@/components/PolicyDetailLink";
import { krwToManwon, manwonToKrw } from "@/lib/profileOptions";

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

const PAGE_SIZE = 10;

export default function PolicyPage() {
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
    // 내 정보에 저장된 값이 있으면 초기값으로 채워준다 — 이후 자유롭게 바꿔서 조회할 수 있다.
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
    <>
      <div className="page-header">
        <h1>
          <span className="icon-box">
            <FaLandmark />
          </span>
          금융 정책 추천
        </h1>
        <p>현재 상황을 입력하면 금융 지원 정책 중 지금 신청 가능한 것만 모아 보여드립니다.</p>
      </div>

      <div className="card">
        <form onSubmit={handleSubmit}>
          <label className="field">
            <span className="field-label">나이</span>
            <input className="input" type="number" value={age} onChange={(e) => setAge(e.target.value)} />
          </label>
          <label className="checkbox-field">
            <input type="checkbox" checked={isMarried} onChange={(e) => setIsMarried(e.target.checked)} />
            기혼
          </label>
          <label className="field">
            <span className="field-label">연소득 (만원)</span>
            <input className="input" type="number" value={income} onChange={(e) => setIncome(e.target.value)} />
          </label>
          {isMarried && (
            <label className="field">
              <span className="field-label">배우자 연소득 (만원, 선택)</span>
              <input
                className="input"
                type="number"
                value={spouseIncome}
                onChange={(e) => setSpouseIncome(e.target.value)}
                placeholder="입력하면 가구소득(본인+배우자) 합산 기준으로 조회해요"
              />
            </label>
          )}
          <label className="field-label" style={{ display: "block" }}>
            지역
          </label>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
            {regions.map((r) => (
              <button
                key={r}
                type="button"
                className="btn-ghost"
                onClick={() => setRegion(r)}
                style={{
                  borderRadius: 999,
                  background: region === r ? "var(--primary-tint)" : undefined,
                  color: region === r ? "var(--primary)" : undefined,
                }}
              >
                {r}
              </button>
            ))}
          </div>
          <button className="btn" type="submit" disabled={loading || !region}>
            {loading ? "찾는 중..." : region ? "금융 정책 찾기" : "지역을 선택해주세요"}
          </button>
        </form>
      </div>

      {error && <p className="error-text" style={{ marginTop: 16 }}>{error}</p>}

      {result && (
        result.options.length === 0 ? (
          <p className="error-text" style={{ marginTop: 16 }}>지금 신청 가능한 금융 정책을 찾지 못했습니다.</p>
        ) : (
          <>
            <div className="result-list">
              {pageOptions.map((option, i) => (
                <div key={i} className="result-item">
                  <div className="result-item-title">
                    {option.is_newlywed_policy && (
                      <span className="badge badge-success" style={{ marginRight: 8 }}>
                        <FaRing /> 신혼부부
                      </span>
                    )}
                    {option.policy_name}
                  </div>
                  <div className="result-item-row">
                    <span>지원 내용</span>
                    <span>{option.benefit_description}</span>
                  </div>
                  <div className="result-item-row">
                    <span>신청 기간</span>
                    <span>{option.application_period}</span>
                  </div>
                  <div style={{ marginTop: 12 }}>
                    <PolicyDetailLink url={option.reference_url} />
                  </div>
                </div>
              ))}
            </div>
            <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
          </>
        )
      )}
    </>
  );
}
