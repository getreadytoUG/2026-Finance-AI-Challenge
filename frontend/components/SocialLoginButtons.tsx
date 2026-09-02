"use client";

import { socialLoginUrl, type SocialProvider } from "@/lib/api";

// 로그인/회원가입 화면 공용. 클릭하면 백엔드 /auth/{provider}/login 으로 브라우저
// 전체 이동 → 백엔드가 카카오 인증 페이지로 302 리다이렉트한다.

function go(provider: SocialProvider) {
  window.location.href = socialLoginUrl(provider);
}

export default function SocialLoginButtons({ action = "로그인" }: { action?: string }) {
  return (
    <div className="grid gap-3">
      <div className="flex items-center gap-3 text-[11px] font-bold text-slate-400">
        <span className="h-px flex-1 bg-slate-200" />
        간편 {action}
        <span className="h-px flex-1 bg-slate-200" />
      </div>
      <button
        type="button"
        onClick={() => go("kakao")}
        className="flex h-12 items-center justify-center gap-2 rounded-xl bg-[#FEE500] text-[13px] font-extrabold text-[#191600] transition hover:brightness-95 active:scale-[.98]"
      >
        <span aria-hidden className="grid h-5 w-5 place-items-center rounded-full bg-[#191600] text-[11px] text-[#FEE500]">K</span>
        카카오로 {action}
      </button>
    </div>
  );
}
