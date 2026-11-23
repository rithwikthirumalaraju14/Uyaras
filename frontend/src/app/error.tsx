"use client";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <section className="section empty">
      <h1>We’ll be right back.</h1>
      <p>
        The store could not load. Make sure the backend and database are
        running.
      </p>
      <button className="pill-button" onClick={reset}>
        Try again
      </button>
    </section>
  );
}
