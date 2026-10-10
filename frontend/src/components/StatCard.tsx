import { type LucideIcon } from "lucide-react";
import { cn } from "@/utils";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  trend?: { value: number; label: string };
  variant?: "brand" | "emerald" | "amber" | "red" | "purple";
  className?: string;
}

const variantStyles = {
  brand: {
    icon: "bg-brand-600/20 text-brand-400 border-brand-500/30",
    glow: "hover:shadow-glow-sm",
  },
  emerald: {
    icon: "bg-emerald-600/20 text-emerald-400 border-emerald-500/30",
    glow: "hover:shadow-[0_0_15px_rgba(52,211,153,0.2)]",
  },
  amber: {
    icon: "bg-amber-600/20 text-amber-400 border-amber-500/30",
    glow: "hover:shadow-[0_0_15px_rgba(251,191,36,0.2)]",
  },
  red: {
    icon: "bg-red-600/20 text-red-400 border-red-500/30",
    glow: "hover:shadow-[0_0_15px_rgba(248,113,113,0.2)]",
  },
  purple: {
    icon: "bg-purple-600/20 text-purple-400 border-purple-500/30",
    glow: "hover:shadow-[0_0_15px_rgba(167,139,250,0.2)]",
  },
};

export function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  variant = "brand",
  className,
}: StatCardProps) {
  const styles = variantStyles[variant];

  return (
    <div
      className={cn(
        "stat-card transition-all duration-300 hover:-translate-y-1 cursor-default",
        styles.glow,
        className
      )}
    >
      <div className="flex items-start justify-between">
        <div
          className={cn(
            "w-11 h-11 rounded-xl border flex items-center justify-center flex-shrink-0",
            styles.icon
          )}
        >
          <Icon className="w-5 h-5" />
        </div>

        {trend && (
          <span
            className={cn(
              "text-xs font-semibold px-2 py-1 rounded-lg",
              trend.value >= 0
                ? "bg-emerald-500/15 text-emerald-400"
                : "bg-red-500/15 text-red-400"
            )}
          >
            {trend.value >= 0 ? "+" : ""}
            {trend.value}% {trend.label}
          </span>
        )}
      </div>

      <div className="mt-2">
        <p className="text-2xl font-bold text-slate-100 tabular-nums">
          {value}
        </p>
        <p className="text-sm font-medium text-slate-400 mt-0.5">{title}</p>
        {subtitle && (
          <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>
        )}
      </div>
    </div>
  );
}
