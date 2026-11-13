import { HTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

export const Badge = forwardRef<HTMLSpanElement, HTMLAttributes<HTMLSpanElement>>(
  ({ className, ...props }, ref) => (
    <span
      ref={ref}
      className={cn(
        "inline-flex items-center rounded-full bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-800",
        className,
      )}
      {...props}
    />
  ),
);

Badge.displayName = "Badge";
