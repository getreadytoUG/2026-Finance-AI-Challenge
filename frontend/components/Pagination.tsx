"use client";

import { useEffect, useState } from "react";

type PaginationProps = {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
};

export default function Pagination({ page, totalPages, onPageChange }: PaginationProps) {
  const [pageInput, setPageInput] = useState(String(page));

  useEffect(() => {
    setPageInput(String(page));
  }, [page]);

  function commitPageInput() {
    const parsed = Number(pageInput);
    if (Number.isInteger(parsed) && parsed >= 1 && parsed <= totalPages) {
      onPageChange(parsed);
    } else {
      setPageInput(String(page));
    }
  }

  if (totalPages <= 1) return null;

  const btnClass =
    "rounded-xl border border-slate-200 bg-white px-4 py-2 text-[12px] font-extrabold text-slate-600 transition hover:border-[#2457d6] hover:text-[#2457d6] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:border-slate-200 disabled:hover:text-slate-600";

  return (
    <div className="mt-5 flex items-center justify-center gap-2">
      <button className={btnClass} type="button" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
        이전
      </button>
      <span className="flex items-center gap-1.5 text-[12px] font-semibold text-slate-400">
        <input
          className="h-9 w-14 rounded-lg border border-slate-200 text-center text-[13px] font-bold text-ink outline-none focus:border-[#2457d6] focus:ring-4 focus:ring-[#2457d6]/10"
          type="number"
          min={1}
          max={totalPages}
          value={pageInput}
          onChange={(e) => setPageInput(e.target.value)}
          onBlur={commitPageInput}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              commitPageInput();
            }
          }}
        />
        <span>/ {totalPages}</span>
      </span>
      <button className={btnClass} type="button" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>
        다음
      </button>
    </div>
  );
}
