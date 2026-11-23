"use client";
import { useState, useSyncExternalStore } from "react";
import { useStore } from "./store-provider";
import { Button } from "./ui/button";
import { Address } from "@/lib/types";
const subscribe = () => () => {};
export function AddressForm({ onSave, initial }: { onSave: (a: Address) => void; initial?: Address }) {
  const { api } = useStore();
  const [message, setMessage] = useState("");
  const hydrated = useSyncExternalStore(subscribe, () => true, () => false);
  return (
    <form
      className="form address-form"
      onSubmit={async (e) => {
        e.preventDefault();
        const form = e.currentTarget;
        try {
          const a = await api<Address>(
            "/addresses" + (initial ? "/" + initial.id : ""),
            Object.fromEntries(new FormData(form)),
            initial ? "PATCH" : "POST",
          );
          onSave(a);
          form.reset();
          setMessage("");
        } catch (e) {
          setMessage((e as Error).message);
        }
      }}
    >
      <h2>{initial ? "Edit address" : "Add an address"}</h2>
      <div className="form-grid">
        {[
          { key: "name", label: "Full name" },
          { key: "phone", label: "Mobile number" },
          { key: "line", label: "Street address" },
          { key: "city", label: "City" },
          { key: "state", label: "State" },
          { key: "pin", label: "PIN code" },
        ].map((f) => (
          <label key={f.key}>
            {f.label}
            <input
              disabled={!hydrated}
              name={f.key}
              defaultValue={initial?.[f.key as keyof Address] || ""}
              required
              maxLength={f.key === "phone" ? 10 : f.key === "pin" ? 6 : 200}
              pattern={
                f.key === "phone"
                  ? "[6-9][0-9]{9}"
                  : f.key === "pin"
                    ? "[1-9][0-9]{5}"
                    : undefined
              }
            />
          </label>
        ))}
      </div>
      <p role="alert">{message}</p>
      <Button type="submit" variant="outline">Save address</Button>
    </form>
  );
}
