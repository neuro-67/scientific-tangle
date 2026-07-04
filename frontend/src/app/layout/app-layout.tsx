import { useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "@/entities/session";
import { ROUTES } from "@/shared/constants";
import { AppLogo } from "@/shared/ui";

const ACTIVE_ROUTE_LABEL: Record<string, string> = {
  [ROUTES.search]: "Новый поиск",
  [ROUTES.history]: "История запросов",
};

const NAV = [
  {
    label: "Новый поиск",
    href: ROUTES.search,
    icon: "/assets/icon-search.png",
  },
  {
    label: "История запросов",
    href: ROUTES.history,
    icon: "/assets/icon-list.png",
  },
];

function UserAvatar({ name }: { name: string }) {
  const initial = name.charAt(0).toUpperCase();
  return (
    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
      {initial}
    </div>
  );
}

/** App shell: collapsible dark sidebar + routed content area. */
export function AppLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const activeLabel = ACTIVE_ROUTE_LABEL[location.pathname];
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-background">
      <aside
        className={`relative flex shrink-0 flex-col bg-sidebar text-sidebar-foreground transition-all duration-300 ease-in-out ${
          isOpen
            ? "w-[260px] p-6"
            : "w-[72px] items-center overflow-hidden px-2 py-6"
        }`}
      >
        {/* Toggle */}
        <button
          type="button"
          onClick={() => setIsOpen((v) => !v)}
          className="flex h-10 w-10 items-center justify-center rounded-xl bg-sidebar-accent/60 text-white/80 transition-colors hover:bg-sidebar-accent hover:text-white"
          title={isOpen ? "Свернуть" : "Развернуть"}
        >
          <svg
            className="h-5 w-5"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M4 6h16M4 12h16M4 18h16"
            />
          </svg>
        </button>

        {/* Logo */}
        <div
          className={`mt-6 flex items-center ${
            isOpen ? "gap-3 px-0 py-1" : "justify-center"
          }`}
        >
          <AppLogo className="h-8 w-8 brightness-0 invert" />
          {isOpen ? (
            <span className="text-base font-semibold">Научный клубок</span>
          ) : null}
        </div>

        <nav className={`flex-1 space-y-1 py-6 ${isOpen ? "" : "w-full"}`}>
          {NAV.map((item) => {
            const active = activeLabel === item.label;
            return (
              <Link
                key={item.label}
                to={item.href}
                className={`flex h-12 items-center gap-3 rounded-xl text-sm font-medium transition-colors ${
                  isOpen ? "px-4" : "justify-center px-0"
                } ${
                  active
                    ? "bg-brand-gradient text-white shadow-sm"
                    : "text-white/70 hover:bg-white/10 hover:text-white"
                }`}
                title={!isOpen ? item.label : undefined}
              >
                <img
                  src={item.icon}
                  alt=""
                  className="h-5 w-5 shrink-0 object-contain brightness-0 invert"
                />
                {isOpen ? item.label : null}
              </Link>
            );
          })}
        </nav>

        <div className={`w-full ${isOpen ? "" : "flex justify-center"}`}>
          <div
            className={`flex items-center rounded-xl bg-sidebar-accent/60 ${
              isOpen ? "gap-3 p-3" : "h-10 w-10 justify-center p-0"
            }`}
          >
            <UserAvatar name={user?.name ?? "R"} />
            {isOpen ? (
              <>
                <div className="flex min-w-0 flex-col">
                  <span className="truncate text-sm font-medium">
                    {user?.name ?? "researcher"}
                  </span>
                  <span className="truncate text-xs text-white/60">
                    {user?.email ?? "researcher@nornickel.ru"}
                  </span>
                </div>
                <button
                  onClick={logout}
                  className="ml-auto rounded-md p-1.5 text-white/70 hover:bg-sidebar-accent hover:text-white"
                  title="Выйти"
                >
                  <img
                    src="/assets/icon-arrow.png"
                    alt="Выйти"
                    className="h-4 w-4 rotate-180 object-contain brightness-0 invert"
                  />
                </button>
              </>
            ) : null}
          </div>
        </div>
      </aside>

      <main className="flex-1 overflow-auto bg-background p-10 pt-8">
        <Outlet />
      </main>
    </div>
  );
}
