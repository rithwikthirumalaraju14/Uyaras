"use client";
import Image from "next/image";
import { useState } from "react";
import { Product } from "@/lib/types";
import { useStore } from "./store-provider";
import { Button } from "./ui/button";
export function MediaManager({
  products,
  onDone,
}: {
  products: Product[];
  onDone: () => void;
}) {
  const { api } = useStore();
  const [message, setMessage] = useState("");
  return (
    <section className="admin-form">
      <h2>Image library</h2>
      <p>
        Descriptions help screen-reader users. Position 0 is the lead image.
        Removing an image detaches it from the product; it does not delete an R2
        object.
      </p>
      <p role="status">{message}</p>
      {products.map((p) => (
        <details key={p.id}>
          <summary>
            {p.name} · {p.images.length} images
          </summary>
          <div className="product-grid">
            {p.images.map((im, index) => (
              <form
                key={im.id}
                className="form"
                onSubmit={async (e) => {
                  e.preventDefault();
                  const f = new FormData(e.currentTarget);
                  try {
                    await api(
                      "/admin/media/" + im.id,
                      {
                        alt: f.get("alt"),
                        position: Number(f.get("position")),
                      },
                      "PATCH",
                    );
                    setMessage("Image updated.");
                    onDone();
                  } catch (e) {
                    setMessage((e as Error).message);
                  }
                }}
              >
                <Image
                  src={im.url}
                  alt={im.alt}
                  width={240}
                  height={260}
                  sizes="240px"
                />
                <label>
                  Description
                  <input
                    name="alt"
                    defaultValue={im.alt}
                    required
                    maxLength={200}
                  />
                </label>
                <label>
                  Position
                  <input
                    name="position"
                    type="number"
                    min="0"
                    max="100"
                    defaultValue={index}
                  />
                </label>
                <Button type="submit">Save image</Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={async () => {
                    try {
                      await api("/admin/media/" + im.id, undefined, "DELETE");
                      setMessage("Image detached.");
                      onDone();
                    } catch (e) {
                      setMessage((e as Error).message);
                    }
                  }}
                >
                  Remove from product
                </Button>
              </form>
            ))}
          </div>
        </details>
      ))}
    </section>
  );
}
