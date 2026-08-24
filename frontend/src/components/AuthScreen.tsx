import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Icon } from "./Icon";
import { ThemeToggle } from "./ThemeToggle";

type AuthScreenProps = {
  mode: "login" | "register";
  error: string;
  onModeChange: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  isDark: boolean;
  onThemeToggle: () => void;
};

export function AuthScreen({
  mode,
  error,
  onModeChange,
  onSubmit,
  isDark,
  onThemeToggle,
}: AuthScreenProps) {
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    setShowPassword(false);
  }, [mode]);

  return (
    <main className="relative grid min-h-svh place-items-center bg-[var(--navy)] p-5 text-white">
      <div className="absolute right-7 top-7">
        <ThemeToggle isDark={isDark} onToggle={onThemeToggle} />
      </div>
      <div className="w-[min(430px,calc(100%-40px))] bg-[#f7f8f4] p-8 text-[var(--ink)] shadow-[20px_20px_0_#253f50] sm:p-12 dark:bg-[#17252c] dark:shadow-[20px_20px_0_#091117]">
        <div className="mb-10 font-mono text-[22px] font-semibold leading-none tracking-[-2px] text-[var(--navy)] sm:mb-[55px]">
          R<span>/</span>G
        </div>
        <p className="m-0 font-mono text-[10px] font-medium tracking-[1.5px] text-[#8b9698]">
          PRIVATE RESEARCH DESK
        </p>
        <h1 className="my-4 text-[37px] font-semibold leading-tight tracking-[-1.7px] text-[var(--navy)]">
          Ask your documents
          <br />
          <em>better questions.</em>
        </h1>
        <p className="mb-7 text-[13px] leading-relaxed text-[#7d898a] dark:text-[#aab8b5]">
          Upload the source material. Get answers grounded in what is actually
          there.
        </p>
        <form onSubmit={onSubmit} className="grid gap-[15px]">
          {mode === "register" && (
            <label className="grid gap-2 font-mono text-[10px] tracking-[1px] text-[#718083] dark:text-[#aab8b5]">
              Name
              <input
                className="border border-[#d4dcd7] bg-white p-[13px] font-sans text-sm text-[var(--ink)] outline-none focus:border-[#9bad9e] dark:border-[#405158] dark:bg-[#1d2d34]"
                name="name"
                required
                placeholder="Your name"
              />
            </label>
          )}
          <label className="grid gap-2 font-mono text-[10px] tracking-[1px] text-[#718083] dark:text-[#aab8b5]">
            Email
            <input
              name="email"
              type="email"
              required
              placeholder="you@company.com"
              className="border border-[#d4dcd7] bg-white p-[13px] font-sans text-sm text-[var(--ink)] outline-none focus:border-[#9bad9e] dark:border-[#405158] dark:bg-[#1d2d34]"
            />
          </label>
          <label className="grid gap-2 font-mono text-[10px] tracking-[1px] text-[#718083] dark:text-[#aab8b5]">
            Password
            <div className="relative">
              <input
                name="password"
                type={showPassword ? "text" : "password"}
                required
                placeholder="••••••••"
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                className="w-full border border-[#d4dcd7] bg-white p-[13px] pr-11 font-sans text-sm text-[var(--ink)] outline-none focus:border-[#9bad9e] dark:border-[#405158] dark:bg-[#1d2d34]"
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                title={showPassword ? "Hide password" : "Show password"}
                className="absolute inset-y-0 right-0 grid w-11 place-items-center border-0 bg-transparent p-0 text-[#718083] hover:text-[var(--ink)] dark:text-[#aab8b5] dark:hover:text-white"
              >
                <Icon name={showPassword ? "eyeOff" : "eye"} size={18} />
              </button>
            </div>
          </label>
          <button
            className="mt-2 inline-flex w-full items-center justify-center gap-2 border-0 bg-[var(--navy)] px-[18px] py-3.5 font-semibold text-white transition hover:-translate-y-px hover:bg-[#24475d] dark:bg-[#d8e4e1] dark:text-[#15242b] dark:hover:bg-[#f0f6f2]"
            type="submit"
          >
            {mode === "login" ? "Enter the desk" : "Create account"}{" "}
            <Icon name="arrow" />
          </button>
        </form>
        <button
          className="mx-auto mt-5 block border-0 bg-transparent text-xs text-[#72817e] underline dark:text-[#aab8b5]"
          onClick={onModeChange}
        >
          {mode === "login"
            ? "New here? Create an account"
            : "Already have an account? Sign in"}
        </button>
        {error && (
          <p className="mt-4 flex items-center gap-1.5 text-xs text-[#b34e3e]">
            <Icon name="alert" />
            {error}
          </p>
        )}
      </div>
      <div className="absolute bottom-7 flex items-center gap-2 font-mono text-[10px] text-[#a9bbc0]">
        <Icon name="book" /> Your files stay tied to your private workspace.
      </div>
    </main>
  );
}
