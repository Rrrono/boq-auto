"use client";

import type { Route } from "next";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "../../components/auth-provider";
import { getErrorMessage, priceCheck, type PriceCheckResponse } from "../../lib/platform-api";

function normalizeQuery(input: string) {
  return input.trim().toLowerCase();
}

const emptyResult: PriceCheckResponse = {
  query: "",
  scanned_jobs: 0,
  observed_rows: 0,
  filtered_rows: 0,
  average_rate: null,
  observations: [],
};

export default function PriceCheckerPage() {
  const router = useRouter();
  const { configured, loading, user, getIdToken } = useAuth();
  const [draftQuery, setDraftQuery] = useState("");
  const [activeQuery, setActiveQuery] = useState("");
  const [result, setResult] = useState<PriceCheckResponse>(emptyResult);
  const [loadingResult, setLoadingResult] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const query = new URLSearchParams(window.location.search).get("q") || "";
    setDraftQuery(query);
    setActiveQuery(query);
  }, []);

  useEffect(() => {
    if (loading || (configured && !user)) {
      return;
    }

    const normalizedQuery = normalizeQuery(activeQuery);
    let cancelled = false;

    async function loadPriceEvidence() {
      setLoadingResult(true);
      setError("");
      try {
        const token = await getIdToken();
        const nextResult = await priceCheck(normalizedQuery, 50, token);
        if (!cancelled) {
          setResult(nextResult);
        }
      } catch (nextError) {
        if (!cancelled) {
          setResult({ ...emptyResult, query: normalizedQuery });
          setError(getErrorMessage(nextError, "Price evidence could not be loaded right now."));
        }
      } finally {
        if (!cancelled) {
          setLoadingResult(false);
        }
      }
    }

    void loadPriceEvidence();
    return () => {
      cancelled = true;
    };
  }, [activeQuery, configured, getIdToken, loading, user]);

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedQuery = normalizeQuery(draftQuery);
    const nextPath = (
      normalizedQuery ? `/price-checker?q=${encodeURIComponent(normalizedQuery)}` : "/price-checker"
    ) as Route;
    setActiveQuery(normalizedQuery);
    router.replace(nextPath);
  }

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
        <form className="form" onSubmit={onSubmit}>
          <label>
            Item description or matched phrase
            <input
              name="q"
              value={draftQuery}
              onChange={(event) => setDraftQuery(event.target.value)}
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

      {error ? (
        <section className="alertCard alertError">
          <strong>Price checker unavailable</strong>
          <p>{error}</p>
        </section>
      ) : null}

      <section className="metaGrid">
        <div className="metaRow">
          <strong>Priced jobs scanned</strong>
          <span>{loadingResult ? "Loading..." : result.scanned_jobs}</span>
        </div>
        <div className="metaRow">
          <strong>Observed rows</strong>
          <span>{loadingResult ? "Loading..." : result.observed_rows}</span>
        </div>
        <div className="metaRow">
          <strong>Filtered results</strong>
          <span>{loadingResult ? "Loading..." : result.filtered_rows}</span>
        </div>
        <div className="metaRow">
          <strong>Average observed rate</strong>
          <span>{loadingResult ? "Loading..." : result.average_rate === null ? "-" : result.average_rate.toLocaleString()}</span>
        </div>
      </section>

      <section className="card">
        <span className="pill">Observed Evidence</span>
        <h3>Recent pricing matches</h3>
        {loadingResult ? (
          <div className="emptyState">Loading recent pricing evidence...</div>
        ) : result.observations.length === 0 ? (
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
