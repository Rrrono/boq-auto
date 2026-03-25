"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "./auth-provider";


export function LoginForm() {
  const router = useRouter();
  const { configured, loading, user, signIn } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const helperText = useMemo(() => {
    if (!configured) {
      return "Firebase Auth is not configured yet. Add Firebase web config values and enable sign-in providers.";
    }
    if (user?.email) {
      return `Signed in as ${user.email}`;
    }
    return "Use a Firebase Auth account with Email/Password enabled. Accounts are created in Firebase Console; self-signup is not live yet.";
  }, [configured, user]);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!configured) {
      setError("Firebase Auth is not configured for this environment yet.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      await signIn(email.trim(), password);
      router.push("/");
      router.refresh();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Sign-in failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="form" onSubmit={onSubmit}>
      <label>
        Work email
        <input
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="name@company.com"
          required
        />
      </label>
      <label>
        Password
        <input
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="Your Firebase Auth password"
          required
        />
      </label>
      <button type="submit" disabled={submitting || loading || !configured}>
        {submitting ? "Signing In..." : "Sign In"}
      </button>
      <p className="helperText">{helperText}</p>
      {error ? <p className="errorText">{error}</p> : null}
    </form>
  );
}
