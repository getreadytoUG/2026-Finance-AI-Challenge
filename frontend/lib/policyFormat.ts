// 온통청년 원본 aplyYmd에 신청 기간이 여러 개면
//   "20260907 ~ 20260928\N20261026 ~ 20261116"
// 처럼 리터럴 "\N"(역슬래시 + 대문자 N — 원본 데이터의 깨진 개행 이스케이프)으로
// 이어붙어 온다. 실제 개행(\n, \r\n)이 섞여 오는 경우도 방어적으로 같이 처리해서,
// 화면에는 ", "로 구분된 한 줄로 보여준다.
//   "20260907 ~ 20260928\N20261026 ~ 20261116"
//   → "20260907 ~ 20260928, 20261026 ~ 20261116"
export function formatApplicationPeriod(raw: string | null | undefined): string {
  if (!raw) return raw ?? "";
  return raw
    .split(/\s*(?:\\N|[\r\n]+)\s*/)
    .map((s) => s.trim())
    .filter(Boolean)
    .join(", ");
}
