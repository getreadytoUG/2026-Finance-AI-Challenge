"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { FaSeedling } from "react-icons/fa6";
import { signup, login, checkEmailAvailable } from "@/lib/api";
import PasswordField from "@/components/PasswordField";
import { OCCUPATION_OPTIONS, REGIONS, manwonToKrw, type OccupationType } from "@/lib/profileOptions";

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [age, setAge] = useState("");
  const [income, setIncome] = useState("");
  const [occupation, setOccupation] = useState<OccupationType | "">("");
  const [region, setRegion] = useState<string | null>(null);
  const [isMarried, setIsMarried] = useState(false);
  const [spouseAge, setSpouseAge] = useState("");
  const [spouseIncome, setSpouseIncome] = useState("");
  const [spouseOccupation, setSpouseOccupation] = useState<OccupationType | "">("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [emailCheckStatus, setEmailCheckStatus] = useState<"idle" | "checking" | "available" | "taken">("idle");
  const router = useRouter();

  async function handleCheckEmail() {
    if (!email) return;
    setEmailCheckStatus("checking");
    try {
      const available = await checkEmailAvailable(email);
      setEmailCheckStatus(available ? "available" : "taken");
    } catch {
      setEmailCheckStatus("idle");
      setError("이메일 확인에 실패했습니다. 다시 시도해주세요.");
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!region || !occupation || emailCheckStatus !== "available") return;
    setError(null);
    setLoading(true);
    try {
      await signup({
        email,
        password,
        age: Number(age),
        is_married: isMarried,
        annual_income_krw: manwonToKrw(Number(income)),
        region,
        occupation,
        spouse_age: isMarried && spouseAge ? Number(spouseAge) : null,
        spouse_annual_income_krw: isMarried && spouseIncome ? manwonToKrw(Number(spouseIncome)) : null,
        spouse_occupation: isMarried && spouseOccupation ? spouseOccupation : null,
      });
      const token = await login(email, password);
      localStorage.setItem("token", token);
      router.push("/policy");
    } catch (err) {
      setError(err instanceof Error ? err.message : "회원가입에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 20,
      }}
    >
      <div className="card" style={{ width: "100%", maxWidth: 420 }}>
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <div className="icon-box icon-box-solid icon-box-lg" style={{ margin: "0 auto 12px" }}>
            <FaSeedling />
          </div>
          <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 4 }}>청년/신혼부부 금융 도우미</h1>
          <p style={{ color: "var(--text-muted)", fontSize: 13 }}>계정을 만들고 나에게 맞는 정책과 리포트를 확인하세요</p>
        </div>
        <form onSubmit={handleSubmit}>
          <label className="field">
            <span className="field-label">이메일</span>
            <div style={{ display: "flex", gap: 8 }}>
              <input
                className="input"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  setEmailCheckStatus("idle");
                }}
                required
                style={{ flex: 1 }}
              />
              <button
                type="button"
                className="btn-ghost"
                onClick={handleCheckEmail}
                disabled={!email || emailCheckStatus === "checking"}
              >
                {emailCheckStatus === "checking" ? "확인 중..." : "중복확인"}
              </button>
            </div>
            {emailCheckStatus === "taken" && (
              <p className="error-text" style={{ marginTop: 6, marginBottom: 0 }}>
                이미 가입된 계정입니다.
              </p>
            )}
            {emailCheckStatus === "available" && (
              <p style={{ marginTop: 6, marginBottom: 0, fontSize: 13, color: "var(--success)" }}>
                사용 가능한 이메일입니다.
              </p>
            )}
          </label>
          <PasswordField label="비밀번호" value={password} onChange={setPassword} />

          <label className="field">
            <span className="field-label">나이</span>
            <input
              className="input"
              type="number"
              min={0}
              placeholder="29"
              value={age}
              onChange={(e) => setAge(e.target.value)}
              required
            />
          </label>
          <label className="field">
            <span className="field-label">연소득 (만원)</span>
            <input
              className="input"
              type="number"
              min={0}
              placeholder="4000"
              value={income}
              onChange={(e) => setIncome(e.target.value)}
              required
            />
          </label>

          <span className="field-label" style={{ display: "block" }}>
            직업 구분
          </span>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
            {OCCUPATION_OPTIONS.map((o) => (
              <button
                key={o.value}
                type="button"
                className="btn-ghost"
                onClick={() => setOccupation(o.value)}
                style={{
                  borderRadius: 999,
                  background: occupation === o.value ? "var(--primary-tint)" : undefined,
                  color: occupation === o.value ? "var(--primary)" : undefined,
                }}
              >
                {o.label}
              </button>
            ))}
          </div>

          <span className="field-label" style={{ display: "block" }}>
            지역
          </span>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
            {REGIONS.map((r) => (
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

          <label className="checkbox-field">
            <input type="checkbox" checked={isMarried} onChange={(e) => setIsMarried(e.target.checked)} />
            기혼
          </label>

          {isMarried && (
            <div
              style={{
                background: "var(--bg)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius-sm)",
                padding: 16,
                marginBottom: 16,
              }}
            >
              <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-muted)", marginBottom: 12 }}>
                배우자 정보 (선택)
              </p>
              <label className="field">
                <span className="field-label">배우자 나이</span>
                <input
                  className="input"
                  type="number"
                  min={0}
                  value={spouseAge}
                  onChange={(e) => setSpouseAge(e.target.value)}
                />
              </label>
              <label className="field">
                <span className="field-label">배우자 연소득 (만원)</span>
                <input
                  className="input"
                  type="number"
                  min={0}
                  value={spouseIncome}
                  onChange={(e) => setSpouseIncome(e.target.value)}
                />
              </label>
              <span className="field-label" style={{ display: "block" }}>
                배우자 직업 구분
              </span>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {OCCUPATION_OPTIONS.map((o) => (
                  <button
                    key={o.value}
                    type="button"
                    className="btn-ghost"
                    onClick={() => setSpouseOccupation(o.value)}
                    style={{
                      borderRadius: 999,
                      background: spouseOccupation === o.value ? "var(--primary-tint)" : undefined,
                      color: spouseOccupation === o.value ? "var(--primary)" : undefined,
                    }}
                  >
                    {o.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {error && <p className="error-text">{error}</p>}
          <button
            className="btn"
            type="submit"
            disabled={loading || !region || !occupation || emailCheckStatus !== "available"}
          >
            {loading ? "가입 중..." : "회원가입"}
          </button>
        </form>
        <p style={{ textAlign: "center", marginTop: 16, fontSize: 13, color: "var(--text-muted)" }}>
          이미 계정이 있으신가요? <Link className="link" href="/login">로그인</Link>
        </p>
      </div>
    </main>
  );
}
