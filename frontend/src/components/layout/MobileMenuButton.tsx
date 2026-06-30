"use client";

import { useUserNav } from "@/providers/UserNavProvider";

export function MobileMenuButton() {
  const { mobileMenuOpen, toggleMobileMenu } = useUserNav();

  return (
    <button
      type="button"
      onClick={toggleMobileMenu}
      className="lg:hidden p-2 -ml-1 rounded-md hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
      aria-expanded={mobileMenuOpen}
      aria-label="Меню"
      data-testid="mobile-menu-toggle"
    >
      <span className="sr-only">Меню</span>
      <span className="flex flex-col justify-center gap-1 w-5 h-5" aria-hidden>
        <span
          className={`block h-0.5 w-5 bg-gray-800 transition-transform ${
            mobileMenuOpen ? "translate-y-1.5 rotate-45" : ""
          }`}
        />
        <span
          className={`block h-0.5 w-5 bg-gray-800 transition-opacity ${
            mobileMenuOpen ? "opacity-0" : ""
          }`}
        />
        <span
          className={`block h-0.5 w-5 bg-gray-800 transition-transform ${
            mobileMenuOpen ? "-translate-y-1.5 -rotate-45" : ""
          }`}
        />
      </span>
    </button>
  );
}
