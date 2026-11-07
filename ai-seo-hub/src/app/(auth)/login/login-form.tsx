"use client";

import { useActionState, useState } from "react";
import { signIn, signUp, type AuthState } from "./actions";

export function LoginForm() {
  const [mode, setMode] = useState<"in" | "up">("in");
  const [state, action, pending] = useActionState<AuthState, FormData>(
    mode === "in" ? signIn : signUp,
    {},
  );
  return (
    <form action={action} className="space-y-4">
      <label className="block text-sm">
        <span className="text-muted">Email</span>
        <input name="email" type="email" required autoComplete="email" className="input mt-1" />
      </label>
      <label className="block text-sm">
        <span className="text-muted">Password</span>
        <input
          name="password" type="password" required minLength={8}
          autoComplete={mode === "in" ? "current-password" : "new-password"}
          className="input mt-1"
        />
      </label>
      {state.error && <p role="alert" className="text-sm text-danger">{state.error}</p>}
      {state.message && <p role="status" className="text-sm text-success">{state.message}</p>}
      <button disabled={pending} className="btn-primary w-full">
        {pending ? "…" : mode === "in" ? "Sign in" : "Create account"}
      </button>
      <button type="button" onClick={() => setMode(mode === "in" ? "up" : "in")}
        className="w-full text-sm text-muted hover:text-foreground">
        {mode === "in" ? "No account? Create one" : "Have an account? Sign in"}
      </button>
    </form>
  );
}
