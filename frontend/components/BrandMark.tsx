// TRINITY2030: trinity_logo.png(글로우 프리즘 마크)를 정사각형 타일로 크롭해 아이콘으로
// 쓰고, 워드마크를 "TRINITY2030"으로 통일한다(2026-09-02 리브랜딩 — 이전엔 커스텀 SVG
// 잎사귀 마크 + "청년/신혼부부 금융 도우미" 텍스트였다). 원본 파일은 1536x1024 검정
// 배경 이미지라 object-cover로 중앙을 정사각 크롭하면 프리즘이 타일 안에 꽉 찬다.
import Image from "next/image";

export function BrandMark({ size = "md", withWordmark = true }: { size?: "sm" | "md" | "lg"; withWordmark?: boolean }) {
  const sizes = { sm: "h-8 w-8", md: "h-10 w-10", lg: "h-12 w-12" };
  const pixelSizes = { sm: 32, md: 40, lg: 48 };
  return (
    <span className="brand-mark inline-flex items-center gap-3">
      <span
        className={`${sizes[size]} grid shrink-0 place-items-center overflow-hidden rounded-[14px] bg-black shadow-[0_8px_20px_rgba(36,87,214,.22)]`}
        aria-hidden="true"
      >
        <Image
          src="/trinity_logo.png"
          alt=""
          width={pixelSizes[size]}
          height={pixelSizes[size]}
          className="h-full w-full object-cover"
        />
      </span>
      {withWordmark && (
        <span className="brand-wordmark text-[15px] font-extrabold tracking-[-0.04em] text-ink">
          TRINITY2030
        </span>
      )}
    </span>
  );
}
