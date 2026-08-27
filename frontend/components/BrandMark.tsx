// 인디고 브리핑: 코발트 사각형과 두 잎·기준선으로 랜딩과 앱을 잇는 선명한 relay mark.
export function BrandMark({ size = "md", withWordmark = true }: { size?: "sm" | "md" | "lg"; withWordmark?: boolean }) {
  const sizes = { sm: "h-8 w-8", md: "h-10 w-10", lg: "h-12 w-12" };
  return (
    <span className="brand-mark inline-flex items-center gap-3">
      <span
        className={`${sizes[size]} grid shrink-0 place-items-center rounded-[14px] bg-[#2457d6] shadow-[0_8px_20px_rgba(36,87,214,.22)]`}
        aria-hidden="true"
      >
        <svg viewBox="0 0 32 32" className="h-[65%] w-[65%]" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M15.8 25.4V12.6" stroke="white" strokeWidth="1.7" strokeLinecap="round" />
          <path
            d="M15.8 17.3C12.9 17.2 9.7 15.7 9.1 11.2C13.9 11.1 16.3 13.6 15.8 17.3Z"
            fill="white"
          />
          <path
            d="M16.1 13.9C16.1 9.4 19.1 7.2 23.2 7.5C22.5 11.7 20.2 14 16.1 13.9Z"
            fill="#B9F0E8"
          />
          <path d="M11.3 25.4H20.5" stroke="white" strokeWidth="1.7" strokeLinecap="round" />
        </svg>
      </span>
      {withWordmark && (
        <span className="brand-wordmark text-[15px] font-extrabold tracking-[-0.04em] text-ink">
          청년/신혼부부 금융 도우미
        </span>
      )}
    </span>
  );
}
