"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { FaSeedling } from "react-icons/fa6";
import { getMe, login } from "@/lib/api";
import PasswordField from "@/components/PasswordField";

export default function LoginPage() {
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
      const token = await login(email, password);
      localStorage.setItem("token", token);
      const profile = await getMe(token);
      router.push(profile.is_admin ? "/admin" : "/policy");
    } catch {
      setError("이메일 또는 비밀번호가 올바르지 않습니다.");
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
          <div className="icon-box icon-box-solid icon-box-lg" style={{ margin: "0 auto 12px" }}>
            <FaSeedling />
          </div>
          <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 4 }}>청년/신혼부부 금융 도우미</h1>
          <p style={{ color: "var(--text-muted)", fontSize: 13 }}>로그인하고 나에게 맞는 정책과 리포트를 확인하세요</p>
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
            {loading ? "로그인 중..." : "로그인"}
          </button>
        </form>
        <p style={{ textAlign: "center", marginTop: 16, fontSize: 13, color: "var(--text-muted)" }}>
          계정이 없으신가요? <Link className="link" href="/signup">회원가입</Link>
        </p>
      </div>
    </main>
  );
}
