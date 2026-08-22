import { useEffect } from "react";
import { Icon } from "./Icon";

export type ToastType = "loading" | "success" | "error" | "info";

export type ToastItem = {
  id: number;
  message: string;
  type: ToastType;
};

export function ToastContainer({
  toasts,
  onDismiss,
}: {
  toasts: ToastItem[];
  onDismiss: (id: number) => void;
}) {
  return (
    <div
      aria-live="polite"
      aria-atomic="false"
      className="pointer-events-none fixed bottom-4 right-4 z-50 flex max-w-[420px] flex-col gap-2"
    >
      {toasts.map((toast) => (
        <div
          key={toast.id}
          role="status"
          className={`pointer-events-auto flex min-w-[280px] items-start gap-3 border bg-white px-4 py-3 shadow-[0_8px_24px_rgba(0,0,0,0.12)] transition-all dark:bg-[#1b2a31] ${
            toast.type === "success"
              ? "border-[#7eb587] text-[var(--ink)]"
              : toast.type === "error"
                ? "border-[#e8a09a] text-[var(--ink)]"
                : toast.type === "loading"
                  ? "border-[var(--line)] text-[var(--ink)]"
                  : "border-[var(--line)] text-[var(--ink)]"
          }`}
        >
          <span className="mt-0.5 shrink-0">
            {toast.type === "loading" && (
              <span className="grid h-4 w-4 animate-spin rounded-full border-2 border-[var(--line)] border-t-[var(--navy)] dark:border-[#2d424d] dark:border-t-[#d8e4e1]" />
            )}
            {toast.type === "success" && (
              <span className="grid h-5 w-5 place-items-center rounded-full bg-[#7eb587] text-white">
                <Icon name="check" size={12} />
              </span>
            )}
            {toast.type === "error" && (
              <span className="grid h-5 w-5 place-items-center rounded-full bg-[#b34e3e] text-white">
                <Icon name="close" size={12} />
              </span>
            )}
            {toast.type === "info" && (
              <span className="grid h-5 w-5 place-items-center rounded-full bg-[var(--navy)] text-white dark:bg-[#d8e4e1] dark:text-[#15242b]">
                <Icon name="file" size={12} />
              </span>
            )}
          </span>
          <p className="flex-1 text-sm leading-snug text-[var(--ink)]">
            {toast.message}
          </p>
          {toast.type !== "loading" && (
            <button
              onClick={() => onDismiss(toast.id)}
              aria-label="Dismiss notification"
              className="shrink-0 border-0 bg-transparent p-1 text-[var(--muted)] hover:text-[var(--ink)]"
            >
              <Icon name="close" size={14} />
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

export function useAutoDismiss(
  toasts: ToastItem[],
  onDismiss: (id: number) => void,
) {
  useEffect(() => {
    const timers = toasts
      .filter((t) => t.type !== "loading")
      .map((t) =>
        setTimeout(() => onDismiss(t.id), t.type === "error" ? 4500 : 3200),
      );
    return () => timers.forEach(clearTimeout);
  }, [toasts, onDismiss]);
}
