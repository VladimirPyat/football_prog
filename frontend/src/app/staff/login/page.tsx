"use client";

import Link from "next/link";
import { LoginForm } from "@/components/auth/LoginForm";

export default function StaffLoginPage() {
  return (
    <div className="max-w-md mx-auto">
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Вход для организаторов</h1>
        <p className="text-gray-600 text-sm mb-6">
          Используйте те же учётные данные, что и для входа организатора или администратора.
        </p>
        <LoginForm />
        <p className="mt-4 text-sm text-center text-gray-500">
          <Link href="/" className="text-blue-600 hover:underline">
            На главную
          </Link>
        </p>
      </div>
    </div>
  );
}
