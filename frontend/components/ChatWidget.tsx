"use client";

import { useState } from "react";
import { MessageCircle, X } from "lucide-react";
import PolicyChat from "@/components/PolicyChat";

export default function ChatWidget() {
  const [open, setOpen] = useState(false);

  return (
    <>
      {open && (
        <div className="fixed bottom-24 right-6 z-50 w-[380px] max-w-[calc(100vw-48px)] animate-fade-up">
          <PolicyChat />
        </div>
      )}
      <button
        type="button"
        className="fixed bottom-6 right-6 z-50 grid h-14 w-14 place-items-center rounded-full bg-[#2457d6] text-white shadow-[0_14px_30px_rgba(36,87,214,.35)] transition hover:-translate-y-0.5 hover:bg-[#1949c1]"
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "정책 챗봇 닫기" : "정책 챗봇 열기"}
      >
        {open ? <X size={22} /> : <MessageCircle size={22} />}
      </button>
    </>
  );
}
