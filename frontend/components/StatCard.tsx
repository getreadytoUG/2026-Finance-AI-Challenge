const ORB_TONE: Record<string, string> = {
  blue: "bg-[#edf3ff]",
  mint: "bg-[#e8f8f4]",
  violet: "bg-[#f0eeff]",
  sky: "bg-[#e9f7fc]",
  orange: "bg-[#fff2e4]",
};

export default function StatCard({
  label,
  value,
  detail,
  tone,
}: {
  label: string;
  value: string;
  detail: string;
  tone: "blue" | "mint" | "violet" | "sky" | "orange";
}) {
  return (
    <div className="relative overflow-hidden rounded-2xl border border-slate-200/80 bg-white p-5">
      <div className={`absolute -right-[22px] -top-7 h-[108px] w-[108px] rounded-full opacity-90 ${ORB_TONE[tone]}`} />
      <div className="relative">
        <div className="text-[11px] font-bold text-slate-400">{label}</div>
        <div className="mt-3 text-[26px] font-extrabold tracking-[-.06em] text-ink">{value}</div>
        <div className="mt-1 text-[11px] font-semibold text-slate-500">{detail}</div>
      </div>
    </div>
  );
}
