"use client";

import { FormEvent, useEffect, useState } from "react";
import { managementApi, StaffUser } from "@/lib/managementApi";
import {
  EmptyState,
  ErrorBanner,
  PageHeader,
  StatusBadge,
} from "@/components/admin/AdminUI";

const roleLabels: Record<string, string> = {
  admin: "Quản trị viên",
  manager: "Quản lý",
  consultant: "Nhân viên tư vấn",
};

export default function UsersPage() {
  const [users, setUsers] = useState<StaffUser[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");

  const load = () =>
    managementApi
      .users()
      .then(setUsers)
      .catch((reason) => setError(reason.message));

  useEffect(() => {
    void load();
  }, []);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await managementApi.createUser({
        full_name: String(form.get("full_name") || ""),
        email: String(form.get("email") || ""),
        role: String(form.get("role") || "consultant"),
      });
      event.currentTarget.reset();
      setShowForm(false);
      load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể tạo người dùng.");
    }
  };

  const toggleStatus = async (user: StaffUser) => {
    try {
      await managementApi.updateUser(user.email, {
        status: user.status === "active" ? "inactive" : "active",
      });
      load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Cập nhật thất bại.");
    }
  };

  return (
    <>
      <PageHeader
        eyebrow="Tổ chức và phân quyền"
        title="Người dùng nội bộ"
        description="Quản lý danh sách Admin, Manager và Consultant cho giai đoạn MVP local."
        action={
          <button
            onClick={() => setShowForm((value) => !value)}
            className="rounded-xl bg-[#cb1d1e] px-4 py-2.5 text-sm font-medium text-white"
          >
            {showForm ? "Đóng biểu mẫu" : "Thêm người dùng"}
          </button>
        }
      />
      {error && <ErrorBanner message={error} />}

      <div className="mb-5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
        MVP chưa có đăng nhập và mật khẩu. Danh sách này dùng để chuẩn bị phân
        công và xác nhận lịch; Authentication sẽ được bổ sung ở giai đoạn sau.
      </div>

      {showForm && (
        <form
          onSubmit={submit}
          className="mb-6 grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:grid-cols-3"
        >
          <label className="text-sm font-medium text-slate-600">
            Họ tên
            <input
              required
              name="full_name"
              className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal outline-none focus:border-red-400"
              placeholder="Nguyễn Văn Tư Vấn"
            />
          </label>
          <label className="text-sm font-medium text-slate-600">
            Email
            <input
              required
              type="email"
              name="email"
              className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal outline-none focus:border-red-400"
              placeholder="nhanvien@company.vn"
            />
          </label>
          <label className="text-sm font-medium text-slate-600">
            Vai trò
            <select
              name="role"
              className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2.5 font-normal outline-none"
            >
              <option value="consultant">Nhân viên tư vấn</option>
              <option value="manager">Quản lý</option>
              <option value="admin">Quản trị viên</option>
            </select>
          </label>
          <button className="rounded-xl bg-[#171b22] px-4 py-2.5 text-sm font-medium text-white md:col-span-3">
            Lưu người dùng
          </button>
        </form>
      )}

      {users.length === 0 ? (
        <EmptyState
          title="Chưa có người dùng nội bộ"
          description="Tạo tài khoản mô tả đầu tiên để chuẩn bị cho bước Authentication."
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {users.map((user) => (
            <article
              key={user.email}
              className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
            >
              <div className="flex items-start gap-4">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-slate-900 text-sm font-bold text-white">
                  {user.full_name
                    .split(" ")
                    .slice(-2)
                    .map((word) => word[0])
                    .join("")
                    .toUpperCase()}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{user.full_name}</p>
                  <p className="mt-1 truncate text-xs text-slate-400">
                    {user.email}
                  </p>
                </div>
                <StatusBadge status={user.status} />
              </div>
              <div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-4">
                <span className="text-sm text-slate-500">
                  {roleLabels[user.role] || user.role}
                </span>
                <button
                  onClick={() => toggleStatus(user)}
                  className="text-xs font-semibold text-[#cb1d1e]"
                >
                  {user.status === "active" ? "Khóa tài khoản" : "Mở lại"}
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </>
  );
}
