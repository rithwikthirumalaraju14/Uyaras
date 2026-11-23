export type Variant = {
  sku: string;
  size: string;
  colour: string;
  price: number;
  regular_price: number | null;
  available: number;
  active: boolean;
};
export type Product = {
  id: string;
  name: string;
  slug: string;
  description: string;
  price: number;
  category: string;
  category_id: string;
  status: string;
  care: string;
  fabric: string;
  cod_allowed: boolean;
  size_guide: string;
  seo_title: string;
  seo_description: string;
  variants: Variant[];
  images: { id: string; url: string; alt: string }[];
};
export type User = { id: string; name: string; email: string; role: string };
export type Auth = { csrf: string; user: User | null; demo: boolean };
export type Address = {
  id: string;
  name: string;
  phone: string;
  line: string;
  city: string;
  state: string;
  pin: string;
};
export type CartLine = {
  sku: string;
  name: string;
  slug: string;
  size: string;
  colour: string;
  price: number;
  quantity: number;
  available: number;
  image: string;
};
export type Cart = { lines: CartLine[]; subtotal: number };
export type Totals = {
  subtotal: number;
  discount: number;
  shipping: number;
  cod_fee: number;
  included_tax: number;
  total: number;
  currency: string;
};
export type Quote = {
  id: string;
  totals: Totals;
  method: string;
  expires: number;
};
export type Order = {
  id: string;
  status: string;
  payment: string;
  method: string;
  demo: boolean;
  totals: Totals;
  address: Address;
  lines: (CartLine & { id: string })[];
  timeline: { message: string; created: number }[];
  shipment: null | { carrier: string; tracking: string; status: string };
  returns: { id: string; status: string; kind: string }[];
  refunds: { amount: number; reference: string }[];
};
export type Storefront = {
  brand: string;
  announcement: string;
  hero_title: string;
  hero_text: string;
  support_email: string;
  returns_policy: string;
  shipping_policy: string;
  cancellation_policy: string;
  privacy_policy: string;
  terms: string;
  refund_policy: string;
  demo: boolean;
};
export const money = (paise: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(paise / 100);
