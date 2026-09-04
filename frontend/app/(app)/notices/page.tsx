"use client";

import { useEffect, useState } from "react";
import { getNotices, type Notice } from "@/lib/api";
import { DashboardLayout } from "@/components/DashboardLayout";

const CATEGORY_STYLE: Record<string, string> = {
  금리: "border-[#2457d6] bg-[#eef3ff] text-[#2457d6]",
  상품: "border-[#7c5cff] bg-[#f2effe] text-[#7c5cff]",
  정책: "border-[#12b886] bg-[#e9f9f3] text-[#12b886]",
  서비스: "border-[#f59f00] bg-[#fff6e0] text-[#c98a00]",
};

const DEFAULT_CATEGORY_STYLE = "border-slate-200 bg-slate-50 text-slate-500";

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("ko-KR", { year: "numeric", month: "long", day: "numeric" });
}

function CategoryBadge({ category }: { category: string }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded-full border px-2.5 py-1 text-[11px] font-extrabold ${CATEGORY_STYLE[category] ?? DEFAULT_CATEGORY_STYLE}`}
    >
      {category}
    </span>
  );
}

export default function NoticesPage() {
  const [notices, setNotices] = useState<Notice[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("token") ?? "";
    getNotices(token)
      .then((res) => setNotices(res.notices))
      .catch((err) => setError(err instanceof Error ? err.message : "공지사항을 불러오지 못했습니다."));
  }, []);

  return (
    <DashboardLayout eyebrow="Notices" title="공지사항">
      {error && (
        <div className="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-[13px] font-semibold text-red-600">
          {error}
        </div>
      )}
      {notices === null && !error && (
        <div className="rounded-[22px] border border-slate-200/80 bg-white p-8 text-center text-[13px] font-semibold text-slate-400">
          불러오는 중...
        </div>
      )}
      {notices !== null && notices.length === 0 && (
        <div className="rounded-[22px] border border-slate-200/80 bg-white p-8 text-center text-[13px] font-semibold text-slate-400">
          등록된 공지사항이 없습니다.
        </div>
      )}
      {notices !== null && notices.length > 0 && (
        <div className="grid gap-3">
          {notices.map((notice) => (
            <article key={notice.id} className="rounded-[22px] border border-slate-200/80 bg-white p-6">
              <div className="mb-3 flex flex-wrap items-center gap-3">
                <CategoryBadge category={notice.category} />
                <span className="text-[12px] font-semibold text-slate-400">{formatDate(notice.created_at)}</span>
              </div>
              <h2 className="mb-2 text-[17px] font-extrabold tracking-[-0.03em] text-ink">{notice.title}</h2>
              <p className="whitespace-pre-line text-[14px] leading-relaxed text-slate-600">{notice.content}</p>
            </article>
          ))}
        </div>
      )}
    </DashboardLayout>
  );
}
