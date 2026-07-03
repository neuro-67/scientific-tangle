import { Link } from "react-router-dom";

import { ROUTES } from "@/shared/constants";
import { Button } from "@/shared/ui";

export function NotFoundPage() {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-4 py-24 text-center">
      <h1 className="text-4xl font-bold">404</h1>
      <p className="text-muted-foreground">Страница не найдена</p>
      <Button asChild>
        <Link to={ROUTES.search}>На главную</Link>
      </Button>
    </div>
  );
}
