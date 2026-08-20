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
  return (
    <main className="auth-screen relative grid min-h-svh place-items-center">
      <ThemeToggle isDark={isDark} onToggle={onThemeToggle} />
      <div className="auth-card w-[min(430px,calc(100%-40px))]">
        <div className="brand-mark">
          R<span>/</span>G
        </div>
        <p className="eyebrow">PRIVATE RESEARCH DESK</p>
        <h1>
          Ask your documents
          <br />
          <em>better questions.</em>
        </h1>
        <p className="auth-copy">
          Upload the source material. Get answers grounded in what is actually
          there.
        </p>
        <form onSubmit={onSubmit} className="auth-form">
          {mode === "register" && (
            <label>
              Name
              <input name="name" required placeholder="Your name" />
            </label>
          )}
          <label>
            Email
            <input
              name="email"
              type="email"
              required
              placeholder="you@company.com"
            />
          </label>
          <label>
            Password
            <input
              name="password"
              type="password"
              required
              placeholder="••••••••"
            />
          </label>
          <button className="primary-button" type="submit">
            {mode === "login" ? "Enter the desk" : "Create account"}{" "}
            <Icon name="arrow" />
          </button>
        </form>
        <button className="text-button" onClick={onModeChange}>
          {mode === "login"
            ? "New here? Create an account"
            : "Already have an account? Sign in"}
        </button>
        {error && (
          <p className="error">
            <Icon name="alert" />
            {error}
          </p>
        )}
      </div>
      <div className="auth-note">
        <Icon name="book" /> Your files stay tied to your private workspace.
      </div>
    </main>
  );
}
