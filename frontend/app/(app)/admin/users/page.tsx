"use client";

import { useEffect, useState } from "react";
import { FaUsers } from "react-icons/fa6";
import { getAdminUsers, type AdminUserItem } from "@/lib/api";
import AdminGuard from "@/components/AdminGuard";
import { OCCUPATION_LABELS, formatDateTime } from "@/components/AdminWidgets";

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
    <div className="card">
      {error && <p className="error-text">{error}</p>}
      {!loaded && !error && <p>불러오는 중...</p>}
      {loaded && users.length > 0 && (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>이메일</th>
                <th>나이</th>
                <th>혼인</th>
                <th>연소득</th>
                <th>지역</th>
                <th>직업</th>
                <th>가입일</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.id}</td>
                  <td>{u.email}</td>
                  <td>{u.age ?? "-"}</td>
                  <td>{u.is_married == null ? "-" : u.is_married ? "기혼" : "미혼"}</td>
                  <td>{u.annual_income_krw != null ? `${u.annual_income_krw.toLocaleString()}원` : "-"}</td>
                  <td>{u.region ?? "-"}</td>
                  <td>{u.occupation ? OCCUPATION_LABELS[u.occupation] ?? u.occupation : "-"}</td>
                  <td>{formatDateTime(u.created_at)}</td>
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
      <div className="page-header">
        <h1>
          <span className="icon-box">
            <FaUsers />
          </span>
          회원
        </h1>
        <p>가입한 회원 목록을 확인하세요.</p>
      </div>
      <UsersContent />
    </AdminGuard>
  );
}
