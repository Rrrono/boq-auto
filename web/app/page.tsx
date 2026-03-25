const cards = [
  {
    title: "Price a BOQ",
    text: "Upload a workbook, route it through the pricing engine, and review matched, flagged, and unmatched lines.",
  },
  {
    title: "Review Extraction",
    text: "Inspect candidate rows and technical attributes pulled from tenders, specs, manuals, and future drawing sources.",
  },
  {
    title: "Check Regional Prices",
    text: "Search an item and compare evidence-backed rates across Nairobi, Mombasa, Kisumu, Eldoret, and beyond.",
  },
];

export default function HomePage() {
  return (
    <div className="stack">
      <section className="hero">
        <span className="eyebrow">Phase 1 Platform</span>
        <h2 className="headline">BOQ workflow and Kenyan price intelligence, together.</h2>
        <p className="lead">
          The first web release is internal-first: jobs, uploads, pricing review, tender extraction, and a region-aware
          price checker. It keeps the BOQ core intact while moving the product toward a real multi-user platform.
        </p>
      </section>
      <section className="grid">
        {cards.map((card) => (
          <article key={card.title} className="card">
            <span className="pill">Phase 1</span>
            <h3>{card.title}</h3>
            <p>{card.text}</p>
          </article>
        ))}
      </section>
    </div>
  );
}
