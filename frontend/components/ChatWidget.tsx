"use client";

import { useState } from "react";
import PolicyChat from "@/components/PolicyChat";

export default function ChatWidget() {
  const [open, setOpen] = useState(false);

  return (
    <>
      {open && (
        <div className="chat-widget-panel">
          <PolicyChat />
        </div>
      )}
      <button
        type="button"
        className="chat-widget-launcher"
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "정책 챗봇 닫기" : "정책 챗봇 열기"}
      >
        {open ? "✕" : "💬"}
      </button>
      {!open && <span className="chat-widget-tooltip">정책 챗봇에게 물어보기</span>}
    </>
  );
}
