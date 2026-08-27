"use client";

import { useEffect, useState } from "react";
import { getAdminUsers, type AdminUserItem } from "@/lib/api";
import AdminGuard from "@/components/AdminGuard";
import { DashboardLayout } from "@/components/DashboardLayout";
import { OCCUPATION_LABELS, formatDateTime } from "@/components/AdminWidgets";

const TH_CLASS = "px-3 py-2.5 text-left text-[12px] font-bold text-slate-400";
const TD_CLASS = "whitespace-nowrap border-t border-slate-100 px-3 py-2.5 text-[13px] text-ink";

function UsersContent() {
  const [users, setUsers] = useState<AdminUserItem[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("token") ?? "";
    getAdminUsers(token)
      .then((res) => setUsers(res.users))
      .catch((err) => setError(err instanceof Error ? err.message : "불러오지 못했습니다."))
      .finally(() => setLoaded(true));
  }, []);

  return (
    <div className="rounded-[22px] border border-slate-200/80 bg-white p-6">
      {error && <p className="text-[13px] font-bold text-rose-500">{error}</p>}
      {!loaded && !error && <p className="text-[13px] text-slate-400">불러오는 중...</p>}
      {loaded && users.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-[13px]">
            <thead>
              <tr>
                <th className={TH_CLASS}>ID</th>
                <th className={TH_CLASS}>이메일</th>
                <th className={TH_CLASS}>나이</th>
                <th className={TH_CLASS}>혼인</th>
                <th className={TH_CLASS}>연소득</th>
                <th className={TH_CLASS}>지역</th>
                <th className={TH_CLASS}>직업</th>
                <th className={TH_CLASS}>가입일</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td className={TD_CLASS}>{u.id}</td>
                  <td className={TD_CLASS}>{u.email}</td>
                  <td className={TD_CLASS}>{u.age ?? "-"}</td>
                  <td className={TD_CLASS}>{u.is_married == null ? "-" : u.is_married ? "기혼" : "미혼"}</td>
                  <td className={TD_CLASS}>{u.annual_income_krw != null ? `${u.annual_income_krw.toLocaleString()}원` : "-"}</td>
                  <td className={TD_CLASS}>{u.region ?? "-"}</td>
                  <td className={TD_CLASS}>{u.occupation ? OCCUPATION_LABELS[u.occupation] ?? u.occupation : "-"}</td>
                  <td className={TD_CLASS}>{formatDateTime(u.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function AdminUsersPage() {
  return (
    <AdminGuard>
      <DashboardLayout eyebrow="ADMIN" title="회원">
        <UsersContent />
      </DashboardLayout>
    </AdminGuard>
  );
}
