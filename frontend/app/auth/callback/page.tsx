"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getMe } from "@/lib/api";
import { BrandMark } from "@/components/BrandMark";

// 소셜 로그인 콜백 착지 지점. 백엔드가 JWT를 URL fragment(#token=...&new=0|1)에
// 실어 여기로 리다이렉트한다. fragment는 서버로 전송되지 않아 접근 로그·Referer에
// 토큰이 남지 않는다.

export default function SocialCallbackPage() {
  const router = useRouter();

  useEffect(() => {
    const params = new URLSearchParams(window.location.hash.replace(/^#/, ""));
    const token = params.get("token");
    if (!token) {
      router.replace("/login?error=oauth");
      return;
    }
    localStorage.setItem("token", token);
    // fragment에서 토큰 흔적을 지운다.
    window.history.replaceState(null, "", window.location.pathname);
    getMe(token)
      .then((me) => {
        // 로그인 상태여도 홈페이지가 먼저 보이도록 바뀌어서(2026-09-02), 이미
        // 프로필을 완성한 기존 유저의 소셜 로그인도 대시보드로 바로 꽂지 않고
        // 홈페이지로 보낸다 — 이메일 로그인(login/page.tsx)과 동일하게 맞춘 것.
        // 프로필을 처음 완성하는 온보딩 직후는 이미 "/"로 보내고 있었다(변경 없음).
        if (me.is_admin) router.replace("/admin");
        else if (!me.profile_complete) router.replace("/onboarding");
        else router.replace("/");
      })
      .catch(() => {
        localStorage.removeItem("token");
        router.replace("/login?error=oauth");
      });
  }, [router]);

  return (
    <div className="grid min-h-screen place-items-center bg-[#f7f9fc]">
      <div className="flex flex-col items-center gap-4">
        <BrandMark size="sm" />
        <p className="text-[13px] font-bold text-slate-400">로그인 중...</p>
      </div>
    </div>
  );
}
