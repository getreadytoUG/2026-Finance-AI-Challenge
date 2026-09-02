"use client";

import { CircleHelp } from "lucide-react";

// 라벨 옆에 붙이는 작은 도움말 툴팁. 물음표 아이콘에 마우스를 올리거나 키보드로
// 포커스하면 말풍선이 뜬다. 별도 의존성 없이 group-hover / focus-within만 쓴다.
export default function InfoTooltip({ text, className = "" }: { text: string; className?: string }) {
  return (
    <span className={`group relative inline-flex align-middle ${className}`}>
      <button
        type="button"
        aria-label="도움말"
        className="inline-flex text-slate-400 transition hover:text-[#2457d6] focus:text-[#2457d6] focus:outline-none"
      >
        <CircleHelp size={14} />
      </button>
      <span
        role="tooltip"
        className="pointer-events-none absolute left-0 top-[calc(100%+6px)] z-30 w-60 max-w-[calc(100vw-4rem)] rounded-lg bg-ink px-3 py-2 text-[11px] font-semibold leading-4 text-white opacity-0 shadow-lg transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100"
      >
        {text}
      </span>
    </span>
  );
}
