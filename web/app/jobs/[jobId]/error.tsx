"use client";

import Link from "next/link";

export default function JobDetailError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="stack">
      <section className="hero">
        <span className="eyebrow">Workspace Error</span>
        <h2 className="headline">This job workspace hit a server-side problem.</h2>
        <p className="lead">
          The page did not finish loading cleanly. You can retry immediately, or go back to the dashboard while we keep
          the rest of the platform stable.
        </p>
      </section>
      <section className="card">
        <span className="pill">What happened</span>
        <p className="helperText">{error.message || "A server-side exception occurred while loading this job."}</p>
        {error.digest ? <p className="monoText">Digest: {error.digest}</p> : null}
        <div className="inlineActions">
          <button type="button" onClick={() => reset()}>
            Retry workspace
          </button>
          <Link className="secondaryButton" href="/">
            Back to dashboard
          </Link>
        </div>
      </section>
    </div>
  );
}
