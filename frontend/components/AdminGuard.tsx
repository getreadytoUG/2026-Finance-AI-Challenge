"use client";

import { useEffect, useState } from "react";
import { getMe } from "@/lib/api";

export default function AdminGuard({ children }: { children: React.ReactNode }) {
  const [access, setAccess] = useState<"loading" | "denied" | "allowed">("loading");

  useEffect(() => {
    const token = localStorage.getItem("token") ?? "";
    getMe(token)
      .then((profile) => setAccess(profile.is_admin ? "allowed" : "denied"))
      .catch(() => setAccess("denied"));
  }, []);

  if (access === "loading") return null;

  if (access === "denied") {
    return (
      <div className="page-header">
        <h1>🛠️ 관리자 대시보드</h1>
        <p className="error-text">관리자 계정으로 로그인해야 볼 수 있는 페이지입니다.</p>
      </div>
    );
  }

  return <>{children}</>;
}
