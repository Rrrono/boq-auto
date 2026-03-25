type SearchParams = Promise<{ q?: string }>;
import { priceCheck } from "../../lib/platform-api";


function normalizeQuery(input: string) {
  return input.trim().toLowerCase();
}


export default async function PriceCheckerPage({ searchParams }: { searchParams: SearchParams }) {
  const { q = "" } = await searchParams;
  const normalizedQuery = normalizeQuery(q);
  const result = await priceCheck(normalizedQuery, 50).catch(() => ({
    query: normalizedQuery,
    scanned_jobs: 0,
    observed_rows: 0,
    filtered_rows: 0,
    average_rate: null,
    observations: [],
  }));

  return (
    <div className="stack">
      <section className="hero">
        <span className="eyebrow">Price Checker</span>
        <h2 className="headline">Search recent priced items and compare observed rates.</h2>
        <p className="lead">
          This Phase 1 checker reads from recent priced jobs, so it already reflects your live BOQ workflow instead of a
          disconnected demo dataset.
        </p>
      </section>

      <section className="card">
        <h3>Search recent pricing evidence</h3>
        <form className="form" action="/price-checker">
          <label>
            Item description or matched phrase
            <input
              name="q"
              defaultValue={q}
              placeholder="concrete, excavation, air conditioner, curtain, survey equipment"
            />
          </label>
          <button type="submit">Search</button>
        </form>
        <p className="helperText">
          This is a bridge feature for Phase 1. Later, the checker should read from canonical items and regional rates in
          the knowledge database.
        </p>
      </section>

      <section className="metaGrid">
        <div className="metaRow">
          <strong>Priced jobs scanned</strong>
          <span>{result.scanned_jobs}</span>
        </div>
        <div className="metaRow">
          <strong>Observed rows</strong>
          <span>{result.observed_rows}</span>
        </div>
        <div className="metaRow">
          <strong>Filtered results</strong>
          <span>{result.filtered_rows}</span>
        </div>
        <div className="metaRow">
          <strong>Average observed rate</strong>
          <span>{result.average_rate === null ? "-" : result.average_rate.toLocaleString()}</span>
        </div>
      </section>

      <section className="card">
        <span className="pill">Observed Evidence</span>
        <h3>Recent pricing matches</h3>
        {result.observations.length === 0 ? (
          <div className="emptyState">
            No priced rows match that search yet. Try a broader phrase or create more priced jobs to build the evidence
            pool.
          </div>
        ) : (
          <div className="tableWrap">
            <table>
              <thead>
                <tr>
                  <th>Job</th>
                  <th>Region</th>
                  <th>Description</th>
                  <th>Match</th>
                  <th>Decision</th>
                  <th>Unit</th>
                  <th>Rate</th>
                  <th>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {result.observations.map((item, index) => (
                  <tr key={`${item.job_title}-${item.description}-${index}`}>
                    <td>{item.job_title}</td>
                    <td>{item.region}</td>
                    <td>{item.description}</td>
                    <td>{item.matched_description || "-"}</td>
                    <td>{item.decision}</td>
                    <td>{item.unit || "-"}</td>
                    <td>{item.rate.toLocaleString()}</td>
                    <td>{item.confidence_score.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
