import { LogOut } from "lucide-react";
import { Link, Outlet } from "react-router-dom";

import { useAuth } from "@/entities/session";
import { ROUTES } from "@/shared/constants";
import { Button } from "@/shared/ui";

/** App shell: top bar with auth state + routed content. */
export function AppLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b">
        <div className="container flex h-14 items-center justify-between">
          <Link to={ROUTES.search} className="font-semibold tracking-tight">
            Научный клубок
          </Link>
          <div className="flex items-center gap-3 text-sm">
            {user ? (
              <span className="text-muted-foreground">
                {user.name}
                <span className="ml-1 hidden sm:inline">({user.role})</span>
              </span>
            ) : null}
            <Button variant="ghost" size="sm" onClick={logout}>
              <LogOut />
              Выйти
            </Button>
          </div>
        </div>
      </header>
      <main className="container flex-1 py-8">
        <Outlet />
      </main>
    </div>
  );
}
