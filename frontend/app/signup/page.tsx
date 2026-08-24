"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { signup, login } from "@/lib/api";
import PasswordField from "@/components/PasswordField";

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await signup(email, password);
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
      <div className="card" style={{ width: "100%", maxWidth: 380 }}>
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <div style={{ fontSize: 28, marginBottom: 8 }}>🌱</div>
          <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 4 }}>청년/신혼부부 금융 도우미</h1>
          <p style={{ color: "var(--text-muted)", fontSize: 13 }}>계정을 만들고 나에게 맞는 정책과 리포트를 확인하세요</p>
        </div>
        <form onSubmit={handleSubmit}>
          <label className="field">
            <span className="field-label">이메일</span>
            <input
              className="input"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>
          <PasswordField label="비밀번호" value={password} onChange={setPassword} />
          {error && <p className="error-text">{error}</p>}
          <button className="btn" type="submit" disabled={loading}>
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
