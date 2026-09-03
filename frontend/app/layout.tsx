import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TRINITY2030: 청년, 정책, 금융이 만나는 원스톱 플랫폼",
  description: "청년 및 신혼부부를 위한 정책·저축·소비 리포트 서비스",
};
 
export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ko">
      <head>
        <link
          rel="stylesheet"
          as="style"
          crossOrigin=""
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
