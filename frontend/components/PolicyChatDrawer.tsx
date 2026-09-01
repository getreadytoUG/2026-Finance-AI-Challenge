"use client";

import { X } from "lucide-react";
import PolicyQaChatPanel, { type PolicyQaTarget } from "@/components/PolicyQaChatPanel";

// 오른쪽에서 슬라이드로 열리는 정책별 챗봇 패널. open이 false가 돼도 transition이
// 끝날 때까지는 item을 그대로 들고 있어야 슬라이드 아웃되는 동안 내용이 안 비워진다
// — 그 타이밍 조율은 호출부(정책 카드 목록 페이지)가 setTimeout으로 담당한다.
export default function PolicyChatDrawer({
  item,
  open,
  onClose,
}: {
  item: PolicyQaTarget | null;
  open: boolean;
  onClose: () => void;
}) {
  return (
    <>
      <div
        className={`fixed inset-0 z-40 bg-ink/20 transition-opacity duration-300 ${open ? "opacity-100" : "pointer-events-none opacity-0"}`}
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        className={`fixed inset-y-0 right-0 z-50 flex w-full max-w-[440px] flex-col bg-[#f7f9fc] shadow-[-20px_0_50px_rgba(15,25,50,.15)] transition-transform duration-300 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between border-b border-slate-200/80 bg-white px-5 py-4">
          <div className="min-w-0">
            <div className="text-[10px] font-extrabold uppercase tracking-[.14em] text-[#2457d6]">AI 정책 챗봇</div>
            <div className="truncate text-[15px] font-extrabold text-ink">{item?.policy_name ?? ""}</div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="닫기"
            className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
          >
            <X size={18} />
          </button>
        </div>
        <div className="min-h-0 flex-1 p-4">{item && <PolicyQaChatPanel item={item} />}</div>
      </div>
    </>
  );
}
