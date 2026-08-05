"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { loadCurrentUser, login } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadCurrentUser()
      .then(() => router.replace("/admin"))
      .catch(() => undefined);
  }, [router]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setLoading(true);
    setError("");
    try {
      await login(String(form.get("email") || ""), String(form.get("password") || ""));
      router.replace("/admin");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Đăng nhập thất bại.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#171b22] px-4">
      <section className="w-full max-w-md rounded-3xl bg-white p-7 shadow-2xl md:p-9">
        <p className="text-xs font-bold uppercase tracking-[0.24em] text-[#cb1d1e]">DC Kaigo</p>
        <h1 className="mt-3 text-2xl font-semibold text-slate-900">Đăng nhập hệ thống quản lý</h1>
        <p className="mt-2 text-sm leading-6 text-slate-500">Dành cho Admin, Manager và nhân viên tư vấn.</p>
        {error && <p className="mt-5 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
        <form onSubmit={submit} className="mt-6 space-y-4">
          <label className="block text-sm font-medium text-slate-700">Email
            <input required type="email" name="email" autoComplete="username" className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 outline-none focus:border-red-400" />
          </label>
          <label className="block text-sm font-medium text-slate-700">Mật khẩu
            <input required minLength={8} type="password" name="password" autoComplete="current-password" className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3 outline-none focus:border-red-400" />
          </label>
          <button disabled={loading} className="w-full rounded-xl bg-[#cb1d1e] px-4 py-3 font-semibold text-white disabled:opacity-60">
            {loading ? "Đang đăng nhập..." : "Đăng nhập"}
          </button>
        </form>
      </section>
    </main>
  );
}
