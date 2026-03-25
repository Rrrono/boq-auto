export default function KnowledgeReviewPage() {
  return (
    <div className="stack">
      <section className="hero">
        <span className="eyebrow">Knowledge Review</span>
        <h2 className="headline">Approve what the platform learns.</h2>
        <p className="lead">
          Candidate rates, aliases, and extracted item updates should land here for review before they become trusted
          knowledge for future pricing.
        </p>
      </section>
      <section className="card">
        <h3>Review queue</h3>
        <p>Expected sections include candidate updates, source provenance, regional conflicts, and approval history.</p>
      </section>
    </div>
  );
}
