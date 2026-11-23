import type { MetadataRoute } from "next";
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      disallow:
        process.env.INDEX_SITE === "true"
          ? ["/admin", "/account", "/checkout", "/cart", "/orders"]
          : ["/"],
    },
    sitemap:
      (process.env.PUBLIC_ORIGIN || "http://localhost:3000") + "/sitemap.xml",
  };
}
