"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const token = await login(email, password);
      localStorage.setItem("token", token);
      router.push("/chat");
    } catch {
      setError("로그인에 실패했습니다.");
    }
  }

  return (
    <main style={{ maxWidth: 360, margin: "80px auto" }}>
      <h1>로그인</h1>
      <form onSubmit={handleSubmit}>
        <input
          type="email"
          placeholder="이메일"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          style={{ display: "block", width: "100%", marginBottom: 8 }}
        />
        <input
          type="password"
          placeholder="비밀번호"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          style={{ display: "block", width: "100%", marginBottom: 8 }}
        />
        {error && <p style={{ color: "red" }}>{error}</p>}
        <button type="submit">로그인</button>
      </form>
    </main>
  );
}
