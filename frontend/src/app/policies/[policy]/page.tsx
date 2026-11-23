import { serverApi } from "@/lib/server-api";
import { Storefront } from "@/lib/types";
import { notFound } from "next/navigation";
export default async function Policy({
  params,
}: {
  params: Promise<{ policy: string }>;
}) {
  const { policy } = await params;
  const s = await serverApi<Storefront>("/storefront");
  const map: Record<string, string> = {
    refunds: s.refund_policy,
    shipping: s.shipping_policy,
    returns: s.returns_policy,
    cancellation: s.cancellation_policy,
    privacy: s.privacy_policy,
    terms: s.terms,
    contact: s.support_email
      ? `Contact Uyaras: ${s.support_email}`
      : "Customer-support details will be published before launch. This preview does not accept real orders.",
  };
  if (!map[policy]) notFound();
  return (
    <section className="section narrow">
      <p className="eyebrow">UYARAS / INFORMATION</p>
      <h1>{policy[0].toUpperCase() + policy.slice(1)}</h1>
      <p className="notice">
        Provisional preview information. Final business policies are pending.
      </p>
      <p className="policy-text">{map[policy]}</p>
    </section>
  );
}
