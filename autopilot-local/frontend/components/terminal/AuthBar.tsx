"use client";

import { useCallback, useEffect, useState } from "react";
import { getApexApiUrl } from "@/lib/backend-urls";
import { Btn } from "@/components/terminal/ui";

type AuthMe = {
  username?: string;
  role?: string;
  is_guest?: boolean;
};

async function authFetch(path: string, init?: RequestInit) {
  return fetch(`${getApexApiUrl()}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
}

export function AuthBar() {
  const [me, setMe] = useState<AuthMe | null>(null);
  const [busy, setBusy] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const res = await authFetch("/api/auth/me");
      if (res.ok) {
        setMe(await res.json());
      } else {
        setMe(null);
      }
    } catch {
      setMe(null);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const guest = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await authFetch("/api/auth/guest", { method: "POST" });
      if (!res.ok) throw new Error(`${res.status}`);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Guest login failed");
    } finally {
      setBusy(false);
    }
  };

  const login = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await authFetch("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) throw new Error(`${res.status}`);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed");
    } finally {
      setBusy(false);
    }
  };

  const logout = async () => {
    setBusy(true);
    try {
      await authFetch("/api/auth/logout", { method: "POST" });
      setMe(null);
    } finally {
      setBusy(false);
    }
  };

  if (me?.username) {
    return (
      <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
        <span>
          {me.username}
          {me.is_guest ? " (guest)" : ""}
        </span>
        <Btn disabled={busy} onClick={() => void logout()}>
          Log out
        </Btn>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <input
        className="rounded border border-[var(--border)] bg-[var(--bg-base)] px-2 py-1 w-28"
        placeholder="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <input
        type="password"
        className="rounded border border-[var(--border)] bg-[var(--bg-base)] px-2 py-1 w-24"
        placeholder="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      <Btn primary disabled={busy} onClick={() => void login()}>
        Login
      </Btn>
      <Btn disabled={busy} onClick={() => void guest()}>
        Guest
      </Btn>
      {error ? <span className="text-red-400">{error}</span> : null}
    </div>
  );
}
