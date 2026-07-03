import { Link, Outlet } from "react-router-dom";

import { ROUTES } from "@/shared/constants";

/** App shell: top bar + routed content. */
export function AppLayout() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b">
        <div className="container flex h-14 items-center justify-between">
          <Link to={ROUTES.search} className="font-semibold tracking-tight">
            Научный клубок
          </Link>
          <nav className="text-sm text-muted-foreground">
            R&amp;D knowledge graph
          </nav>
        </div>
      </header>
      <main className="container flex-1 py-8">
        <Outlet />
      </main>
    </div>
  );
}
