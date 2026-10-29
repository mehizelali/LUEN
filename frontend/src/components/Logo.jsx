import { cn } from "@/lib/utils";

/** Flat aperture mark — matches Lumen’s calm product UI */
function Mark({ className }) {
  return (
    <svg
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn("size-7 shrink-0", className)}
      aria-hidden
    >
      <rect width="64" height="64" rx="14" fill="#003049" />
      <circle cx="32" cy="32" r="14" stroke="#FFFFFF" strokeWidth="3.5" />
      <circle cx="32" cy="32" r="5" fill="#FFFFFF" />
    </svg>
  );
}

export function Logo({ className, markClassName, showWordmark = true }) {
  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      <Mark className={markClassName} />
      {showWordmark ? (
        <span className="truncate text-[15px] font-semibold tracking-[-0.03em] text-[#003049]">
          Lumen
        </span>
      ) : (
        <span className="sr-only">Lumen</span>
      )}
    </div>
  );
}
