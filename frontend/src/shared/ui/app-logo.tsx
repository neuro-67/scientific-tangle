import { cn } from "@/shared/lib/utils";

type Props = {
  className?: string;
};

/** App brand logo: 3D atom illustration used next to the app name. */
export function AppLogo({ className }: Props) {
  return (
    <img
      src="/assets/illustration-atom.png"
      alt="Научный клубок"
      className={cn("h-8 w-8 object-contain", className)}
    />
  );
}
