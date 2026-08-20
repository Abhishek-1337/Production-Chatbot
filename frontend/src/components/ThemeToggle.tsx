import { Icon } from "./Icon";

type ThemeToggleProps = {
  isDark: boolean;
  onToggle: () => void;
};

export function ThemeToggle({ isDark, onToggle }: ThemeToggleProps) {
  return (
    <button
      className="grid h-[34px] w-[34px] place-items-center border border-[var(--line)] bg-[var(--paper)] text-[var(--muted)] transition hover:border-[var(--amber)] hover:text-[var(--amber)]"
      type="button"
      onClick={onToggle}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      aria-pressed={isDark}
      title={isDark ? "Switch to light mode" : "Switch to dark mode"}
    >
      <Icon name={isDark ? "sun" : "moon"} size={16} />
    </button>
  );
}
