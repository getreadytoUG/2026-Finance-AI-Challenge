"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowRight, Check, Mail, ShieldCheck } from "lucide-react";
import { getMe, login } from "@/lib/api";
import PasswordField from "@/components/PasswordField";
import { BrandMark } from "@/components/BrandMark";

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
      router.push(profile.is_admin ? "/admin" : "/dashboard");
    } catch {
      setError("이메일 또는 비밀번호가 올바르지 않습니다.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#f7f9fc] text-ink">
      <header className="border-b border-slate-100 bg-white">
        <div className="mx-auto flex max-w-[1180px] items-center justify-between px-5 py-4 lg:px-0">
          <Link href="/">
            <BrandMark size="sm" />
          </Link>
          <Link href="/signup" className="text-[13px] font-bold text-slate-500 transition hover:text-[#2457d6]">
            처음이신가요? <span className="text-[#2457d6]">회원가입</span>
          </Link>
        </div>
      </header>
      <main className="grid min-h-[calc(100vh-73px)] lg:grid-cols-[.95fr_1.05fr]">
        <section className="relative hidden overflow-hidden bg-[#0d1b36] p-12 text-white lg:flex lg:flex-col lg:justify-between">
          <div className="absolute inset-0 bg-[linear-gradient(145deg,#0d1b36,rgba(36,87,214,.55))]" />
          <div className="relative">
            <div className="mb-16 text-[10px] font-extrabold uppercase tracking-[.2em] text-[#9cc5ff]">YOUR POLICY BRIEFING</div>
            <h1 className="max-w-[510px] text-[45px] font-extrabold leading-[1.14] tracking-[-.075em]">
              오늘의 정책,
              <br />
              <span className="text-[#9cc5ff]">내 계획에 맞춰</span>
              <br />
              다시 정리했어요.
            </h1>
            <p className="mt-6 max-w-[390px] text-[14px] leading-7 text-blue-100/75">
              로그인하면 나에게 맞는 지원 정책과 AI 분석 리포트, 저축플랜을 한 화면에서 확인할 수 있어요.
            </p>
          </div>
          <div className="relative flex items-center gap-3 text-[12px] font-bold text-blue-100/75">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-white/10">
              <ShieldCheck size={17} />
            </span>
            공공 정책 데이터 기반의 개인 맞춤 브리핑
          </div>
        </section>
        <section className="flex items-center justify-center px-5 py-14 sm:px-10">
          <div className="w-full max-w-[410px]">
            <div className="mb-8">
              <div className="section-kicker">SIGN IN TO YOUR PLAN</div>
              <h2 className="mt-3 text-[30px] font-extrabold tracking-[-.06em]">내 브리핑을 이어볼까요?</h2>
              <p className="mt-3 text-[13px] text-slate-500">로그인하고 나에게 맞는 정책과 리포트를 확인하세요.</p>
            </div>
            <form onSubmit={handleSubmit} className="grid gap-5">
              <label className="grid gap-2 text-[12px] font-extrabold text-slate-700">
                이메일
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={17} strokeWidth={1.8} />
                  <input
                    className="h-12 w-full rounded-xl border border-slate-200 bg-white pl-11 pr-4 text-[13px] font-semibold outline-none transition placeholder:text-slate-400 focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
                    type="email"
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
              </label>
              <PasswordField label="비밀번호" value={password} onChange={setPassword} />
              {error && <p className="-mt-2 text-[12px] font-bold text-rose-500">{error}</p>}
              <button
                type="submit"
                disabled={loading}
                className="group mt-1 flex h-12 items-center justify-center gap-2 rounded-xl bg-[#2457d6] text-[13px] font-extrabold text-white shadow-[0_12px_22px_rgba(36,87,214,.2)] transition hover:-translate-y-0.5 hover:bg-[#1949c1] active:scale-[.98] disabled:opacity-60"
              >
                {loading ? "로그인 중..." : "로그인"} <ArrowRight size={16} className="transition group-hover:translate-x-1" />
              </button>
            </form>
            <div className="mt-7 flex items-center justify-center gap-1.5 text-[11px] font-semibold text-slate-400">
              <Check size={14} className="text-[#1eb8a6]" />
              안전한 로그인
            </div>
            <p className="mt-12 text-center text-[12px] text-slate-400">
              계정이 없으신가요?{" "}
              <Link href="/signup" className="font-extrabold text-[#2457d6]">
                회원가입 <ArrowRight className="inline" size={12} />
              </Link>
            </p>
          </div>
        </section>
      </main>
    </div>
  );
}
