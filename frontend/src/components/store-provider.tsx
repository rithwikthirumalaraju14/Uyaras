"use client";
import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useRef,
  ReactNode,
} from "react";
import type { Auth } from "@/lib/types";
type Context = {
  auth: Auth | null;
  ready: boolean;
  api: <T>(
    path: string,
    body?: unknown,
    method?: string,
    headers?: Record<string, string>,
  ) => Promise<T>;
  refresh: () => Promise<void>;
};
const StoreContext = createContext<Context | null>(null);
export function StoreProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<Auth | null>(null);
  const [ready, setReady] = useState(false);
  const sessionRef = useRef<Auth | null>(null);
  const pending = useRef<Promise<Auth> | null>(null);
  const initialize = useCallback((): Promise<Auth> => {
    if (!pending.current) {
      pending.current = fetch("/api/v1/session")
        .then(async (r) => {
          if (!r.ok) throw new Error("Unable to start your session. Please try again.");
          const session = (await r.json()) as Auth;
          sessionRef.current = session;
          setAuth(session);
          setReady(true);
          return session;
        })
        .finally(() => { pending.current = null; });
    }
    return pending.current;
  }, []);
  const refresh = useCallback(async () => { await initialize(); }, [initialize]);
  useEffect(() => {
    void initialize().catch(() => setReady(true));
  }, [initialize]);
  const api = useCallback(
    async <T,>(
      path: string,
      body?: unknown,
      method?: string,
      headers?: Record<string, string>,
    ): Promise<T> => {
      const session = sessionRef.current || await initialize();
      const r = await fetch("/api/v1" + path, {
        method: method || (body === undefined ? "GET" : "POST"),
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": session.csrf,
          ...headers,
        },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      const data = await r.json();
      if (!r.ok)
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Please check the form fields and try again.",
        );
      if (data.csrf) {
        sessionRef.current = data as Auth;
        setAuth(data as Auth);
      }
      return data as T;
    },
    [initialize],
  );
  return (
    <StoreContext.Provider value={{ auth, ready, api, refresh }}>
      {children}
    </StoreContext.Provider>
  );
}
export function useStore() {
  const value = useContext(StoreContext);
  if (!value) throw new Error("Store provider missing");
  return value;
}
