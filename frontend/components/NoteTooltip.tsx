"use client";

import { useEffect, useRef, useState } from "react";
import { AlertCircle } from "lucide-react";

// 안내 아이콘 팝오버. 브라우저 기본 title= 은 클릭에 반응하지 않고 hover 후 한참
// 있어야 떠서(트랙패드/모바일에선 아예 안 뜸), 클릭 토글 + hover 로 모두 열리는
// 말풍선으로 만든다. 바깥 클릭 / Esc 로 닫힌다. uppercase·tracking 을 걸어둔 헤더
// 안에 들어가는 경우가 있어 말풍선 본문은 normal-case·tracking-normal 로 되돌린다.
export default function NoteTooltip({
  text,
  triggerClassName,
  bubbleClassName,
  iconSize = 13,
  ariaLabel = "안내",
}: {
  text: string;
  triggerClassName: string;
  bubbleClassName: string;
  iconSize?: number;
  ariaLabel?: string;
}) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!open) return;
    function onDocPointer(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDocPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <span
      ref={wrapRef}
      className="relative inline-flex"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        type="button"
        aria-label={ariaLabel}
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className={`inline-flex shrink-0 cursor-pointer ${triggerClassName}`}
      >
        <AlertCircle size={iconSize} />
      </button>
      <span
        role="tooltip"
        className={`absolute left-0 top-[calc(100%+6px)] z-30 w-64 max-w-[calc(100vw-4rem)] rounded-lg px-3 py-2 text-[11px] font-semibold normal-case leading-4 tracking-normal shadow-lg transition-opacity duration-150 ${bubbleClassName} ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
      >
        {text}
      </span>
    </span>
  );
}
