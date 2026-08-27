type PolicyDetailLinkProps = {
  url: string;
  style?: React.CSSProperties;
  className?: string;
};

// 온통청년 API의 신청 URL(aplyUrlAddr)이 비어있는 정책이 실측 기준 전체의 약
// 20%(참고 URL로도 못 채우는 경우)라, href=""로 렌더하면 클릭 시 그냥 같은
// 페이지로 돌아온 것처럼 보인다(2026-08-26 발견) — url이 없으면 클릭 불가능한
// 안내 텍스트로 대체한다.
export default function PolicyDetailLink({ url, style, className }: PolicyDetailLinkProps) {
  if (!url) {
    return (
      <span className={`text-[13px] font-bold text-slate-400 ${className ?? ""}`} style={style}>
        링크 정보 없음
      </span>
    );
  }
  return (
    <a
      className={`text-[13px] font-bold text-[#2457d6] hover:underline ${className ?? ""}`}
      href={url}
      target="_blank"
      rel="noreferrer"
      style={style}
    >
      자세히 보기 →
    </a>
  );
}
