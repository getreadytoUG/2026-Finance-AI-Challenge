// 인디고 브리핑: 페이지마다 다른 eyebrow/title/action을 가진 편집형 헤더.
// 사이드바+topbar 셸은 AppShell(진짜 Next.js layout)이 담당하므로, 여기서는
// 그 안에 들어갈 페이지 헤더 + 본문 래퍼만 그린다.
export function DashboardLayout({
  children,
  title,
  eyebrow,
  action,
}: {
  children: React.ReactNode;
  title: string;
  eyebrow: string;
  action?: React.ReactNode;
}) {
  return (
    <>
      <div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <div className="mb-2 text-[10px] font-extrabold uppercase tracking-[0.2em] text-[#2457d6]">{eyebrow}</div>
          <h1 className="text-[30px] font-extrabold tracking-[-0.055em] text-ink sm:text-[38px]">{title}</h1>
        </div>
        {action}
      </div>
      {children}
    </>
  );
}

export function SectionLabel({ children, action }: { children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="mb-4 flex items-center justify-between">
      <h2 className="text-[15px] font-extrabold tracking-[-0.03em] text-ink">{children}</h2>
      {action}
    </div>
  );
}
