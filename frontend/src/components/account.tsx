"use client";
import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useStore } from "@/components/store-provider";
import { Button } from "@/components/ui/button";
import { AddressForm } from "@/components/address-form";
import { Address, User } from "@/lib/types";
export default function Account({ initialToken }: { initialToken: string }) {
  const { auth, ready, api, refresh } = useStore();
  const [mode, setMode] = useState(initialToken ? "reset" : "login");
  const [message, setMessage] = useState("");
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [editingAddress, setEditingAddress] = useState<Address | undefined>();
  const [busy, setBusy] = useState(false);
  const token = initialToken;
  useEffect(() => {
    if (auth?.user)
      api<{ addresses: Address[] }>("/me")
        .then((r) => setAddresses(r.addresses))
        .catch((e) => setMessage(e.message));
  }, [auth?.user, api]);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setMessage("");
    const f = new FormData(e.currentTarget);
    try {
      if (mode === "reset") {
        const r = await api<{ message: string }>("/auth/reset", {
          token,
          password: f.get("password"),
        });
        setMessage(r.message);
        setMode("login");
        await refresh();
      } else if (mode === "forgot") {
        const r = await api<{ message: string }>("/auth/forgot", {
          email: f.get("email"),
        });
        setMessage(r.message);
      } else {
        const body: Record<string, unknown> = {
          email: f.get("email"),
          password: f.get("password"),
        };
        if (mode === "register") body.name = f.get("name");
        await api("/auth/" + mode, body);
      }
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  if (!ready) return <section className="section">Loading account…</section>;
  return (
    <section className="section narrow">
      <p className="eyebrow">YOUR LITTLE CORNER</p>
      <h1>
        {auth?.user
          ? `Hello, ${auth.user.name}.`
          : mode === "register"
            ? "Make yourself at home."
            : mode === "forgot"
              ? "Let’s get you back in."
              : mode === "reset"
                ? "A fresh start."
                : "Welcome back."}
      </h1>
      <p role="status">{message}</p>
      {auth?.user ? (
        <>
          <div className="account-nav">
            <Link href="/orders">Your orders →</Link>
            <Link href="/checkout">Continue checkout →</Link>
            {auth.user.role !== "Customer" && (
              <Link href="/admin">Open staff studio →</Link>
            )}
          </div>
          <form
            className="form"
            onSubmit={async (e) => {
              e.preventDefault();
              try {
                await api<User>(
                  "/me",
                  { name: new FormData(e.currentTarget).get("name") },
                  "PATCH",
                );
                await refresh();
                setMessage("Profile updated.");
              } catch (e) {
                setMessage((e as Error).message);
              }
            }}
          >
            <label>
              Your name
              <input
                name="name"
                defaultValue={auth.user.name}
                required
                maxLength={100}
              />
            </label>
            <Button type="submit">Save profile</Button>
          </form>
          <h2>Saved addresses</h2>
          {addresses.map((a) => (
            <article className="address-card" key={a.id}>
              <strong>{a.name}</strong>
              <p>
                {a.line}, {a.city}, {a.state} {a.pin}
              </p>
              <Button
                variant="outline" onClick={() => setEditingAddress(a)}
              >Edit address</Button>
              <Button
                variant="outline"
                onClick={async () => {
                  try {
                    await api("/addresses/" + a.id, undefined, "DELETE");
                    setAddresses(addresses.filter((x) => x.id !== a.id));
                  } catch (e) {
                    setMessage((e as Error).message);
                  }
                }}
              >
                Delete address
              </Button>
            </article>
          ))}
          <AddressForm
            key={editingAddress?.id || "new"}
            initial={editingAddress}
            onSave={(a) => {
              setAddresses(current => editingAddress ? current.map(x => x.id === a.id ? a : x) : [...current, a]);
              setEditingAddress(undefined);
              setMessage("Address saved.");
            }}
          />
          {editingAddress && <Button variant="ghost" onClick={()=>setEditingAddress(undefined)}>Cancel editing</Button>}
          <Button
            variant="outline"
            onClick={async () => {
              await api("/auth/logout", {});
              setAddresses([]);
            }}
          >
            Sign out
          </Button>
        </>
      ) : (
        <>
          <div className="tabs">
            <Button
              variant={mode === "login" ? "default" : "outline"}
              onClick={() => setMode("login")}
            >
              Sign in
            </Button>
            <Button
              variant={mode === "register" ? "default" : "outline"}
              onClick={() => setMode("register")}
            >
              Create account
            </Button>
          </div>
          <form className="form" onSubmit={submit}>
            {mode === "register" && (
              <label>
                Your name
                <input
                  name="name"
                  autoComplete="name"
                  required
                  maxLength={100}
                />
              </label>
            )}
            {mode !== "reset" && (
              <label>
                Email
                <input
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                />
              </label>
            )}
            {mode !== "forgot" && (
              <label>
                Password
                <input
                  name="password"
                    aria-label="Password"
                    aria-describedby="password-hint"
                  type="password"
                  minLength={12}
                  maxLength={128}
                  autoComplete={
                    mode === "login" ? "current-password" : "new-password"
                  }
                  required
                />
                  <small id="password-hint">At least 12 characters.</small>
              </label>
            )}
            <Button type="submit" disabled={busy}>
              {busy
                ? "Please wait…"
                : mode === "register"
                  ? "Create account"
                  : mode === "forgot"
                    ? "Send recovery link"
                    : mode === "reset"
                      ? "Update password"
                      : "Sign in"}
            </Button>
          </form>
          <Button variant="ghost" onClick={() => setMode("forgot")}>
            Forgot your password?
          </Button>
          <p className="muted">
            Development preview: use fictional information. Email delivery
            requires an SMTP configuration.
          </p>
        </>
      )}
    </section>
  );
}
