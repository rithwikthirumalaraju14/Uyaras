import Link from "next/link";
export default function NotFound() {
  return (
    <section className="section empty">
      <h1>This page wandered off.</h1>
      <Link href="/products">Back to the collection →</Link>
    </section>
  );
}
