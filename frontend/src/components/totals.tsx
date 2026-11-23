import { Totals, money } from "@/lib/types";
export function OrderTotals({ totals: t }: { totals: Totals }) {
  return (
    <dl className="totals">
      <div>
        <dt>Items</dt>
        <dd>{money(t.subtotal)}</dd>
      </div>
      <div>
        <dt>Discount</dt>
        <dd>−{money(t.discount)}</dd>
      </div>
      <div>
        <dt>Shipping</dt>
        <dd>{money(t.shipping)}</dd>
      </div>
      <div>
        <dt>COD fee</dt>
        <dd>{money(t.cod_fee)}</dd>
      </div>
      <div className="total">
        <dt>Total</dt>
        <dd>{money(t.total)}</dd>
      </div>
      <div className="muted">
        <dt>Included provisional tax</dt>
        <dd>{money(t.included_tax)}</dd>
      </div>
    </dl>
  );
}
