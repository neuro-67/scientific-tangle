import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";

import { cn } from "@/shared/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-ring",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground",
        secondary: "border-transparent bg-secondary text-secondary-foreground",
        outline: "text-foreground",
        // Domain variants driven by index.css semantic colors.
        confidenceHigh:
          "border-transparent bg-[hsl(var(--confidence-high-bg))] text-[hsl(var(--confidence-high))]",
        confidenceMedium:
          "border-transparent bg-[hsl(var(--confidence-medium-bg))] text-[hsl(var(--confidence-medium))]",
        confidenceLow:
          "border-transparent bg-[hsl(var(--confidence-low-bg))] text-[hsl(var(--confidence-low))]",
        geoRu: "border-transparent bg-geo-ru/15 text-geo-ru",
        geoForeign: "border-transparent bg-geo-foreign/15 text-geo-foreign",
        gap: "border-transparent bg-gap/15 text-gap",
        contradiction:
          "border-transparent bg-contradiction/15 text-contradiction",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

type Props = React.ComponentProps<"span"> & VariantProps<typeof badgeVariants>;

function Badge({ className, variant, ...props }: Props) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
