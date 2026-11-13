import { type ButtonHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

type ButtonVariant = "primary" | "secondary" | "quiet";

const variants: Record<ButtonVariant, string> = {
  primary: "bg-emerald-700 text-white hover:bg-emerald-800 focus-visible:ring-emerald-700",
  secondary:
    "border border-slate-300 bg-white text-slate-900 hover:border-emerald-600 hover:text-emerald-800 focus-visible:ring-emerald-700",
  quiet: "text-slate-600 hover:bg-slate-100 hover:text-slate-950 focus-visible:ring-slate-500",
};

export const Button = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }
>(({ className, variant = "primary", ...props }, ref) => (
  <button
    ref={ref}
    className={cn(
      "inline-flex min-h-11 items-center justify-center rounded-xl px-5 py-3 text-sm font-bold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
      variants[variant],
      className,
    )}
    {...props}
  />
));

Button.displayName = "Button";
