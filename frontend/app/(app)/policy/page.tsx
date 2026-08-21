"use client";

import { useState } from "react";
import { callTool } from "@/lib/api";

type PolicyOption = {
  policy_name: string;
  eligible: boolean;
  benefit_description: string;
  application_period: string;
  reference_url: string;
};

type PolicyMatchOutput = {
  options: PolicyOption[];
};

export default function PolicyPage() {
  const [age, setAge] = useState("29");
  const [isMarried, setIsMarried] = useState(false);
  const [income, setIncome] = useState("40000000");
  const [region, setRegion] = useState("서울");
  const [result, setResult] = useState<PolicyMatchOutput | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    setLoading(true);
    const token = localStorage.getItem("token") ?? "";
    try {
      const output = await callTool<PolicyMatchOutput>(token, "policy_matcher", {
        age: Number(age),
        is_married: isMarried,
        annual_income_krw: Number(income),
        region,
      });
      setResult(output);
    } catch (err) {
      setError(err instanceof Error ? err.message : "요청이 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>🏛️ 정책비교</h1>
        <p>현재 상황을 입력하면 청년/신혼부부 정책의 가/불가 여부와 우대금리를 비교해드립니다.</p>
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
            <span className="field-label">연소득 (원)</span>
            <input className="input" type="number" value={income} onChange={(e) => setIncome(e.target.value)} />
          </label>
          <label className="field">
            <span className="field-label">지역</span>
            <input className="input" type="text" value={region} onChange={(e) => setRegion(e.target.value)} />
          </label>
          <button className="btn" type="submit" disabled={loading}>
            {loading ? "비교 중..." : "정책 비교하기"}
          </button>
        </form>
      </div>

      {error && <p className="error-text" style={{ marginTop: 16 }}>{error}</p>}

      {result && (
        <div className="result-list">
          {result.options.map((option, i) => (
            <div key={i} className="result-item">
              <div className="result-item-title">{option.policy_name}</div>
              <div className="result-item-row">
                <span>가능 여부</span>
                <span className={`badge ${option.eligible ? "badge-success" : "badge-danger"}`}>
                  {option.eligible ? "가능" : "불가"}
                </span>
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
                <a className="link" href={option.reference_url} target="_blank" rel="noreferrer">
                  자세히 보기 →
                </a>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
