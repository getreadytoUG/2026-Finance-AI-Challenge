const STATUS_PILL: Record<string, string> = {
  임박: "urgent",
  만료: "urgent",
  여유: "available",
  상시: "available",
  예정: "neutral",
};

export default function StatusPill({ status }: { status: string }) {
  return (
    <span className={`policy-status ${STATUS_PILL[status] ?? "neutral"}`}>
      <span />
      {status}
    </span>
  );
}
