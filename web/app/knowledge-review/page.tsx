"use client";

import { useEffect, useState } from "react";

import { useAuth } from "../../components/auth-provider";
import { getErrorMessage, getKnowledgeQueue, type KnowledgeQueueResponse } from "../../lib/platform-api";

const emptyQueue: KnowledgeQueueResponse = {
  scanned_jobs: 0,
  candidate_count: 0,
  unmatched_count: 0,
  review_count: 0,
  candidates: [],
};

export default function KnowledgeReviewPage() {
  const { configured, loading, user, getIdToken } = useAuth();
  const [queue, setQueue] = useState<KnowledgeQueueResponse>(emptyQueue);
  const [loadingQueue, setLoadingQueue] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (loading || (configured && !user)) {
      return;
    }

    let cancelled = false;

    async function loadQueue() {
      setLoadingQueue(true);
      setError("");
      try {
        const token = await getIdToken();
        const nextQueue = await getKnowledgeQueue(40, token);
        if (!cancelled) {
          setQueue(nextQueue);
        }
      } catch (nextError) {
        if (!cancelled) {
          setQueue(emptyQueue);
          setError(getErrorMessage(nextError, "The knowledge review queue could not be loaded right now."));
        }
      } finally {
        if (!cancelled) {
          setLoadingQueue(false);
        }
      }
    }

    void loadQueue();
    return () => {
      cancelled = true;
    };
  }, [configured, getIdToken, loading, user]);

  return (
    <div className="stack">
      <section className="hero">
        <span className="eyebrow">Knowledge Review</span>
        <h2 className="headline">Surface weak pricing decisions before they harden into knowledge.</h2>
        <p className="lead">
          This queue is a Phase 1 bridge from pricing output into the future review and learning workflow. It reads the
          live flagged and unmatched rows from recent jobs so the team can see where the library still struggles.
        </p>
      </section>

      {error ? (
        <section className="alertCard alertError">
          <strong>Review queue unavailable</strong>
          <p>{error}</p>
        </section>
      ) : null}

      <section className="metaGrid">
        <div className="metaRow">
          <strong>Priced jobs scanned</strong>
          <span>{loadingQueue ? "Loading..." : queue.scanned_jobs}</span>
        </div>
        <div className="metaRow">
          <strong>Review queue</strong>
          <span>{loadingQueue ? "Loading..." : queue.candidate_count}</span>
        </div>
        <div className="metaRow">
          <strong>Unmatched lines</strong>
          <span>{loadingQueue ? "Loading..." : queue.unmatched_count}</span>
        </div>
        <div className="metaRow">
          <strong>Manual review lines</strong>
          <span>{loadingQueue ? "Loading..." : queue.review_count}</span>
        </div>
      </section>

      <section className="card">
        <span className="pill">Live Queue</span>
        <h3>Flagged rows from recent jobs</h3>
        {loadingQueue ? (
          <div className="emptyState">Loading recent review candidates...</div>
        ) : queue.candidates.length === 0 ? (
          <div className="emptyState">
            No flagged rows are available yet. Once more jobs are priced, this page will highlight the weakest matching
            areas for review-first database improvement.
          </div>
        ) : (
          <div className="tableWrap">
            <table>
              <thead>
                <tr>
                  <th>Job</th>
                  <th>Region</th>
                  <th>Description</th>
                  <th>Current match</th>
                  <th>Decision</th>
                  <th>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {queue.candidates.map((item, index) => (
                  <tr key={`${item.job_title}-${item.description}-${index}`}>
                    <td>{item.job_title}</td>
                    <td>{item.region}</td>
                    <td>{item.description}</td>
                    <td>{item.matched_description || "-"}</td>
                    <td>{item.decision}</td>
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
