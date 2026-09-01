"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ShieldCheck } from "lucide-react";
import { getMe, updateProfile, isTokenExpired, type ProfileInput, type UserProfile } from "@/lib/api";
import ProfileFieldsForm from "@/components/ProfileFieldsForm";
import { BrandMark } from "@/components/BrandMark";

// 소셜 로그인으로 처음 들어온 유저가 필수 프로필(나이/소득/지역/직업)을 채우는 화면.
// AppShell(로그인 후 레이아웃)이 profile_complete=false인 유저를 여기로 강제한다.

export default function OnboardingPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token || isTokenExpired(token)) {
      localStorage.removeItem("token");
      router.replace("/login");
      return;
    }
    getMe(token)
      .then((me) => {
        // 이미 프로필이 완성돼 있으면 온보딩을 건너뛴다.
        if (me.profile_complete) {
          router.replace(me.is_admin ? "/admin" : "/dashboard");
          return;
        }
        setProfile(me);
        setReady(true);
      })
      .catch(() => {
        localStorage.removeItem("token");
        router.replace("/login?error=oauth");
      });
  }, [router]);

  async function handleSubmit(input: ProfileInput) {
    const token = localStorage.getItem("token") ?? "";
    await updateProfile(token, input);
    router.replace("/dashboard");
  }

  if (!ready) return null;

  return (
    <div className="min-h-screen bg-[#f7f9fc] text-ink">
      <header className="border-b border-slate-100 bg-white">
        <div className="mx-auto flex max-w-[1180px] items-center justify-between px-5 py-4 lg:px-0">
          <Link href="/">
            <BrandMark size="sm" />
          </Link>
          <span className="text-[13px] font-bold text-slate-400">{profile?.email}</span>
        </div>
      </header>
      <main className="mx-auto max-w-[560px] px-5 py-14">
        <div className="section-kicker">ALMOST THERE</div>
        <h1 className="mt-3 text-[30px] font-extrabold tracking-[-.06em]">프로필만 채우면 끝나요</h1>
        <p className="mt-3 text-[13px] text-slate-500">
          입력한 정보는 정책 매칭·저축플랜 계산에만 쓰이고, 언제든 내 정보 화면에서 수정할 수 있어요.
        </p>
        <div className="mt-8 rounded-[26px] border border-slate-200/80 bg-white p-6 shadow-[0_20px_55px_rgba(22,45,84,.08)] sm:p-9">
          <ProfileFieldsForm
            initial={profile}
            submitLabel="시작하기"
            submittingLabel="저장 중..."
            onSubmit={handleSubmit}
          />
        </div>
        <div className="mt-6 flex items-center justify-center gap-1.5 text-[11px] font-semibold text-slate-400">
          <ShieldCheck size={14} className="text-[#1eb8a6]" />
          입력한 정보는 정책 매칭에만 사용
        </div>
      </main>
    </div>
  );
}
