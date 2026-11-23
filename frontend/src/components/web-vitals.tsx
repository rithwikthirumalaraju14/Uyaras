"use client";
import { useReportWebVitals } from "next/web-vitals";
const report: Parameters<typeof useReportWebVitals>[0] = metric => {
  if (process.env.NEXT_PUBLIC_MEASURE_VITALS !== "true") return;
  // No query strings, account IDs, metric IDs or customer data are transmitted.
  const segment = location.pathname.split("/")[1] || "home";
  const route = ["home", "products", "cart", "checkout", "account", "orders", "admin", "policies", "offers"].includes(segment) ? segment : "other";
  navigator.sendBeacon("/api/v1/metrics/vitals", new Blob([JSON.stringify({name:metric.name,value:metric.value,route})], {type:"application/json"}));
};
export function WebVitals() { useReportWebVitals(report); return null; }
