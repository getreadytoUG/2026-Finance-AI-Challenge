// 백엔드 compute_policy_status()는 신청 마감일(apply_end_ymd)이 없으면 "상시"를
// 반환한다. 하지만 실측상(캐시 2,744건 중 ~1,365건) 이건 "연중 상시 모집"이 아니라
// 온통청년 원본에 신청기간 데이터가 아예 없어서 마감 여부를 알 수 없는 경우가
// 대부분이다 — 초록불로 보이면 "지금 신청 가능"으로 오해하므로, 붉은 계열 배지 +
// "기간 확인 필요"로 표시한다. 백엔드가 주는 status 문자열("상시")은 그대로 두고
// (API 계약/필터 값), 프론트에서 라벨과 색만 바꾼다.
const STATUS_PILL: Record<string, string> = {
  임박: "urgent",
  만료: "urgent",
  여유: "available",
  상시: "unknown",
  예정: "neutral",
};

const STATUS_LABEL: Record<string, string> = {
  상시: "기간 확인 필요",
};

export default function StatusPill({ status }: { status: string }) {
  return (
    <span className={`policy-status ${STATUS_PILL[status] ?? "neutral"}`}>
      <span />
      {STATUS_LABEL[status] ?? status}
    </span>
  );
}
