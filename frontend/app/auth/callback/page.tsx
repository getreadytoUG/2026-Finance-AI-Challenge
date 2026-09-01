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
        if (me.is_admin) router.replace("/admin");
        else if (!me.profile_complete) router.replace("/onboarding");
        else router.replace("/dashboard");
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
