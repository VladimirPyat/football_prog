import type { Metadata } from "next";
import { AuthProvider } from "@/providers/AuthProvider";
import { ContestProvider } from "@/providers/ContestProvider";
import { ToastProvider } from "@/providers/ToastProvider";
import { AppShell } from "@/components/layout/AppShell";
import { TempPasswordGuard } from "@/components/auth/TempPasswordGuard";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sport Prognosis",
  description: "Конкурс спортивных прогнозов",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru">
      <body className="antialiased">
        <AuthProvider>
          <ContestProvider>
            <ToastProvider>
              <TempPasswordGuard />
              <AppShell>{children}</AppShell>
            </ToastProvider>
          </ContestProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
