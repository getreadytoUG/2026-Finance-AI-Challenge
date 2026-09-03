"use client";

import { CalendarClock, Tag } from "lucide-react";
import PolicyDetailLink from "@/components/PolicyDetailLink";
import StatusPill from "@/components/StatusPill";
import type { PolicyBrowseItem } from "@/lib/api";
import { formatApplicationPeriod } from "@/lib/policyFormat";

// 정책 "문서" 읽기 화면 — 백엔드 _policy_text()가 챗봇 프롬프트에 넣는 정보와
// 사람이 보는 필드가 1:1 대응되도록 구성한다(정책명/분야/설명/신청기간/상태).
export default function PolicyDetailPanel({ item }: { item: PolicyBrowseItem }) {
  return (
    <div className="flex h-full flex-col rounded-[22px] border border-slate-200/80 bg-white p-5">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-[17px] font-extrabold tracking-[-.03em] text-ink">{item.policy_name}</h2>
        <StatusPill status={item.status} />
      </div>

      <div className="mt-4 flex flex-col gap-2.5 text-[12px] font-bold text-slate-500">
        <div className="flex items-center gap-2">
          <Tag size={14} className="text-slate-400" />
          {item.large_category}
        </div>
        <div className="flex items-center gap-2">
          <CalendarClock size={14} className="text-slate-400" />
          신청 기간 {formatApplicationPeriod(item.application_period)}
        </div>
      </div>

      <div className="mt-5 min-h-0 flex-1 overflow-y-auto rounded-xl bg-[#f7f9fc] p-4 text-[13px] leading-relaxed whitespace-pre-wrap text-slate-600">
        {item.benefit_description}
      </div>

      <div className="mt-4">
        <PolicyDetailLink url={item.reference_url} />
      </div>
    </div>
  );
}
