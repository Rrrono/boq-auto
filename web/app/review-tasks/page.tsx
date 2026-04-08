"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { useAuth } from "../../components/auth-provider";
import {
  type ReviewTaskBridgeSummary,
  type ReviewTask,
  claimReviewTask,
  getReviewTaskBridgeSummary,
  getErrorMessage,
  listReviewTasks,
  qaReviewTask,
  syncReviewTaskBridge,
  submitReviewTask,
} from "../../lib/platform-api";

function formatReason(reason: string) {
  return reason.replaceAll("_", " ");
}

type ReviewDraft = {
  decision: string;
  matched_description: string;
  rate: string;
  reviewer_note: string;
  qa_status: string;
  qa_note: string;
};

export default function ReviewTasksPage() {
  const { configured, loading, user, getIdToken } = useAuth();
  const [tasks, setTasks] = useState<ReviewTask[]>([]);
  const [loadingTasks, setLoadingTasks] = useState(true);
  const [tasksError, setTasksError] = useState("");
  const [bridge, setBridge] = useState<ReviewTaskBridgeSummary | null>(null);
  const [bridgeError, setBridgeError] = useState("");
  const [statusFilter, setStatusFilter] = useState("open");
  const [qaFilter, setQaFilter] = useState("");
  const [promotionFilter, setPromotionFilter] = useState("");
  const [mineOnly, setMineOnly] = useState(false);
  const [savingTaskId, setSavingTaskId] = useState<number | null>(null);
  const [syncingBridge, setSyncingBridge] = useState(false);
  const [drafts, setDrafts] = useState<Record<number, ReviewDraft>>({});

  useEffect(() => {
    if (loading || (configured && !user)) {
      return;
    }

    let cancelled = false;
    async function loadTasks() {
      setLoadingTasks(true);
      setTasksError("");
      try {
        const token = await getIdToken();
        const nextTasks = await listReviewTasks(
          {
            status: statusFilter || undefined,
            qa_status: qaFilter || undefined,
            promotion_status: promotionFilter || undefined,
            mine: mineOnly,
          },
          token,
        );
        if (!cancelled) {
          setTasks(nextTasks);
        }
        const bridgeSummary = await getReviewTaskBridgeSummary(token);
        if (!cancelled) {
          setBridge(bridgeSummary);
          setBridgeError("");
        }
      } catch (error) {
        if (!cancelled) {
          setTasks([]);
          setTasksError(getErrorMessage(error, "The reviewer task queue could not be loaded."));
          setBridge(null);
          setBridgeError(getErrorMessage(error, "The learning bridge summary could not be loaded."));
        }
      } finally {
        if (!cancelled) {
          setLoadingTasks(false);
        }
      }
    }

    void loadTasks();
    return () => {
      cancelled = true;
    };
  }, [configured, getIdToken, loading, mineOnly, promotionFilter, qaFilter, statusFilter, user]);

  const summary = useMemo(() => {
    const counts = new Map<string, number>();
    for (const task of tasks) {
      counts.set(task.status, (counts.get(task.status) ?? 0) + 1);
    }
    return {
      open: counts.get("open") ?? 0,
      claimed: counts.get("claimed") ?? 0,
      submitted: counts.get("submitted") ?? 0,
    };
  }, [tasks]);

  function getDraft(task: ReviewTask): ReviewDraft {
    return drafts[task.id] ?? {
      decision: task.decision === "unmatched" ? "manual_rate" : "confirm_match",
      matched_description: task.matched_description,
      rate: "",
      reviewer_note: "",
      qa_status: task.qa_status === "pending" ? "approved" : task.qa_status,
      qa_note: task.qa_note,
    };
  }

  async function refreshTasks() {
    const token = await getIdToken();
    const nextTasks = await listReviewTasks(
      {
        status: statusFilter || undefined,
        qa_status: qaFilter || undefined,
        promotion_status: promotionFilter || undefined,
        mine: mineOnly,
      },
      token,
    );
    setTasks(nextTasks);
    const bridgeSummary = await getReviewTaskBridgeSummary(token);
    setBridge(bridgeSummary);
  }

  async function onSyncBridge() {
    setSyncingBridge(true);
    setBridgeError("");
    setTasksError("");
    try {
      const token = await getIdToken();
      const response = await syncReviewTaskBridge(token);
      setBridge(response.bridge);
      await refreshTasks();
    } catch (error) {
      setBridgeError(getErrorMessage(error, "The workbook bridge could not be synced."));
    } finally {
      setSyncingBridge(false);
    }
  }

  async function onClaim(taskId: number) {
    setSavingTaskId(taskId);
    setTasksError("");
    try {
      const token = await getIdToken();
      await claimReviewTask(taskId, token);
      await refreshTasks();
    } catch (error) {
      setTasksError(getErrorMessage(error, "This task could not be claimed."));
    } finally {
      setSavingTaskId(null);
    }
  }

  async function onSubmit(task: ReviewTask) {
    const draft = getDraft(task);
    setSavingTaskId(task.id);
    setTasksError("");
    try {
      const token = await getIdToken();
      await submitReviewTask(
        task.id,
        {
          decision: draft.decision,
          matched_description: draft.matched_description,
          rate: draft.rate.trim() ? Number(draft.rate) : null,
          reviewer_note: draft.reviewer_note,
        },
        token,
      );
      await refreshTasks();
    } catch (error) {
      setTasksError(getErrorMessage(error, "This review could not be submitted."));
    } finally {
      setSavingTaskId(null);
    }
  }

  async function onQaSubmit(task: ReviewTask) {
    const draft = getDraft(task);
    setSavingTaskId(task.id);
    setTasksError("");
    try {
      const token = await getIdToken();
      await qaReviewTask(
        task.id,
        {
          qa_status: draft.qa_status,
          qa_note: draft.qa_note,
        },
        token,
      );
      await refreshTasks();
    } catch (error) {
      setTasksError(getErrorMessage(error, "The QA decision could not be saved."));
    } finally {
      setSavingTaskId(null);
    }
  }

  return (
    <div className="stack">
      <section className="hero">
        <span className="eyebrow">Reviewer Workflow</span>
        <h2 className="headline">Review tasks turn weak BOQ rows into claimable work.</h2>
        <p className="lead">
          This is the first step toward a reviewer marketplace workflow: the engine surfaces uncertain lines, and
          reviewers claim, decide, and submit structured corrections instead of teaching the platform through scattered manual steps.
        </p>
      </section>

      {tasksError ? (
        <section className="alertCard alertError">
          <strong>Reviewer queue unavailable</strong>
          <p>{tasksError}</p>
        </section>
      ) : null}

      <section className="metaGrid">
        <div className="metaRow">
          <strong>Open</strong>
          <span>{loadingTasks ? "Loading..." : summary.open}</span>
        </div>
        <div className="metaRow">
          <strong>Claimed</strong>
          <span>{loadingTasks ? "Loading..." : summary.claimed}</span>
        </div>
        <div className="metaRow">
          <strong>Submitted</strong>
          <span>{loadingTasks ? "Loading..." : summary.submitted}</span>
        </div>
        <div className="metaRow">
          <strong>QA-ready</strong>
          <span>{loadingTasks ? "Loading..." : tasks.filter((task) => task.status === "submitted").length}</span>
        </div>
        <div className="metaRow">
          <strong>Promotion-ready</strong>
          <span>{loadingTasks ? "Loading..." : tasks.filter((task) => task.promotion_status === "ready").length}</span>
        </div>
        <div className="metaRow">
          <strong>Signed in reviewer</strong>
          <span>{user?.email || "Unknown reviewer"}</span>
        </div>
        <div className="metaRow">
          <strong>Queue scope</strong>
          <span>{mineOnly ? "My tasks only" : "Shared queue"}</span>
        </div>
      </section>

      <section className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <div>
            <span className="pill">Learning Bridge</span>
            <h3>Reviewer artifacts to workbook review</h3>
            <p className="helperText" style={{ marginTop: 8 }}>
              Approved reviewer outcomes first land in the normalized sidecar, then this bridge syncs them back into
              workbook-era <span className="monoText">CandidateMatches</span> so the older promotion commands keep working.
            </p>
          </div>
          <button type="button" onClick={() => void onSyncBridge()} disabled={syncingBridge || !bridge?.available}>
            {syncingBridge ? "Syncing bridge..." : "Sync to workbook review"}
          </button>
        </div>
        {bridgeError ? <p className="helperText" style={{ color: "var(--danger)" }}>{bridgeError}</p> : null}
        {!bridge?.available ? (
          <div className="emptyState">The bridge is not available until the API can see both the production workbook and normalized schema.</div>
        ) : (
          <>
            <div className="metaGrid">
              <div className="metaRow">
                <strong>Rate observations</strong>
                <span>{bridge.rate_observations}</span>
              </div>
              <div className="metaRow">
                <strong>Alias suggestions</strong>
                <span>{bridge.alias_suggestions}</span>
              </div>
              <div className="metaRow">
                <strong>Candidate review records</strong>
                <span>{bridge.candidate_review_records}</span>
              </div>
              <div className="metaRow">
                <strong>Synced candidate rows</strong>
                <span>{bridge.synced_candidate_rows}</span>
              </div>
              <div className="metaRow">
                <strong>Pending workbook candidates</strong>
                <span>{bridge.pending_workbook_candidates}</span>
              </div>
            </div>
            <p className="helperText">
              Workbook: <span className="monoText">{bridge.workbook_path}</span>
            </p>
            <p className="helperText">
              Schema: <span className="monoText">{bridge.schema_path}</span>
            </p>
          </>
        )}
      </section>

      <section className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <div>
            <span className="pill">Queue</span>
            <h3>Current review tasks</h3>
          </div>
          <label>
            Status
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
              <option value="open">Open</option>
              <option value="claimed">Claimed</option>
              <option value="submitted">Submitted</option>
              <option value="">All</option>
            </select>
          </label>
          <label>
            QA
            <select value={qaFilter} onChange={(event) => setQaFilter(event.target.value)}>
              <option value="">All</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="escalated">Escalated</option>
            </select>
          </label>
          <label>
            Promotion
            <select value={promotionFilter} onChange={(event) => setPromotionFilter(event.target.value)}>
              <option value="">All</option>
              <option value="pending">Pending</option>
              <option value="ready">Ready</option>
              <option value="logged">Logged</option>
              <option value="needs_attention">Needs attention</option>
              <option value="closed">Closed</option>
            </select>
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <input type="checkbox" checked={mineOnly} onChange={(event) => setMineOnly(event.target.checked)} />
            My tasks only
          </label>
        </div>

        {loadingTasks ? (
          <div className="emptyState">Loading review tasks...</div>
        ) : tasks.length === 0 ? (
          <div className="emptyState">No review tasks match this filter yet. Sync tasks from a priced job workspace first.</div>
        ) : (
          <div className="stack">
            {tasks.map((task) => {
              const draft = getDraft(task);
              const claimedByCurrentUser = Boolean(user?.uid && task.reviewer_uid && task.reviewer_uid === user.uid);
              return (
                <article key={task.id} className="card">
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                    <div>
                      <span className="pill">{task.status}</span>
                      <h3>{task.description}</h3>
                      <p className="helperText">
                        Job <Link href={`/jobs/${task.job_id}`}>{task.job_id}</Link> - {task.sheet_name || "Sheet"} row {task.row_number}
                      </p>
                    </div>
                    <div className="triageStack">
                      <span className={`confidenceBadge confidence-${task.confidence_band}`}>{task.confidence_band}</span>
                      <div className="triageScore">Score {task.confidence_score.toFixed(2)}</div>
                    </div>
                  </div>

                  <div className="metaGrid">
                    <div className="metaRow">
                      <strong>Task type</strong>
                      <span>{task.task_type.replaceAll("_", " ")}</span>
                    </div>
                    <div className="metaRow">
                      <strong>Engine decision</strong>
                      <span>{task.decision}</span>
                    </div>
                    <div className="metaRow">
                      <strong>Current match</strong>
                      <span>{task.matched_description || "-"}</span>
                    </div>
                    <div className="metaRow">
                      <strong>Matched item code</strong>
                      <span className="monoText">{task.matched_item_code || "-"}</span>
                    </div>
                    <div className="metaRow">
                      <strong>Unit</strong>
                      <span>{task.unit || "-"}</span>
                    </div>
                    <div className="metaRow">
                      <strong>Reviewer</strong>
                      <span>{task.reviewer_email || "Unassigned"}</span>
                    </div>
                    <div className="metaRow">
                      <strong>QA status</strong>
                      <span>{task.qa_status}</span>
                    </div>
                    <div className="metaRow">
                      <strong>Promotion</strong>
                      <span>{task.promotion_target ? `${task.promotion_target} - ${task.promotion_status}` : task.promotion_status}</span>
                    </div>
                  </div>

                  <div className="card" style={{ marginTop: 14 }}>
                    <span className="pill">Reviewer brief</span>
                    <p className="helperText" style={{ marginTop: 8 }}>{task.task_question}</p>
                    {task.response_schema.length > 0 ? (
                      <div className="reasonList" style={{ marginTop: 10 }}>
                        {task.response_schema.map((field) => (
                          <span key={field} className="reasonBadge">
                            {formatReason(field)}
                          </span>
                        ))}
                      </div>
                    ) : null}
                  </div>

                  {task.flag_reasons.length > 0 ? (
                    <div className="reasonList">
                      {task.flag_reasons.map((reason) => (
                        <span key={reason} className="reasonBadge">
                          {formatReason(reason)}
                        </span>
                      ))}
                    </div>
                  ) : null}

                  {task.status === "open" ? (
                    <div className="inlineActions">
                      <button type="button" onClick={() => void onClaim(task.id)} disabled={savingTaskId === task.id}>
                        {savingTaskId === task.id ? "Claiming..." : "Claim task"}
                      </button>
                    </div>
                  ) : null}

                  {(task.status === "claimed" && claimedByCurrentUser) || task.status === "submitted" ? (
                    <form
                      className="form"
                      onSubmit={(event) => {
                        event.preventDefault();
                        void onSubmit(task);
                      }}
                    >
                      <label>
                        Reviewer decision
                        <select
                          value={draft.decision}
                          onChange={(event) =>
                            setDrafts((current) => ({
                              ...current,
                              [task.id]: { ...draft, decision: event.target.value },
                            }))
                          }
                          disabled={task.status === "submitted"}
                        >
                          <option value="confirm_match">Confirm current match</option>
                          <option value="manual_rate">Use manual rate</option>
                          <option value="no_good_match">No good match yet</option>
                        </select>
                      </label>
                      <label>
                        Match description
                        <input
                          type="text"
                          value={draft.matched_description}
                          onChange={(event) =>
                            setDrafts((current) => ({
                              ...current,
                              [task.id]: { ...draft, matched_description: event.target.value },
                            }))
                          }
                          disabled={task.status === "submitted"}
                        />
                      </label>
                      <label>
                        Manual rate
                        <input
                          type="number"
                          step="0.01"
                          value={draft.rate}
                          onChange={(event) =>
                            setDrafts((current) => ({
                              ...current,
                              [task.id]: { ...draft, rate: event.target.value },
                            }))
                          }
                          disabled={task.status === "submitted"}
                        />
                      </label>
                      <label>
                        Reviewer note
                        <textarea
                          rows={3}
                          value={draft.reviewer_note}
                          onChange={(event) =>
                            setDrafts((current) => ({
                              ...current,
                              [task.id]: { ...draft, reviewer_note: event.target.value },
                            }))
                          }
                          disabled={task.status === "submitted"}
                        />
                      </label>
                      {task.status === "submitted" ? (
                        <p className="helperText">Submitted {task.submitted_at ? new Date(task.submitted_at).toLocaleString() : ""}</p>
                      ) : (
                        <button type="submit" disabled={savingTaskId === task.id}>
                          {savingTaskId === task.id ? "Submitting..." : "Submit review"}
                        </button>
                      )}
                    </form>
                  ) : null}

                  {task.status === "submitted" ? (
                    <form
                      className="form"
                      onSubmit={(event) => {
                        event.preventDefault();
                        void onQaSubmit(task);
                      }}
                    >
                      <label>
                        QA outcome
                        <select
                          value={draft.qa_status}
                          onChange={(event) =>
                            setDrafts((current) => ({
                              ...current,
                              [task.id]: { ...draft, qa_status: event.target.value },
                            }))
                          }
                        >
                          <option value="approved">Approved</option>
                          <option value="rejected">Rejected</option>
                          <option value="escalated">Escalated</option>
                        </select>
                      </label>
                      <label>
                        QA note
                        <textarea
                          rows={2}
                          value={draft.qa_note}
                          onChange={(event) =>
                            setDrafts((current) => ({
                              ...current,
                              [task.id]: { ...draft, qa_note: event.target.value },
                            }))
                          }
                        />
                      </label>
                      <button type="submit" disabled={savingTaskId === task.id}>
                        {savingTaskId === task.id ? "Saving QA..." : "Save QA state"}
                      </button>
                      <p className="helperText">
                        Current QA owner: {task.qa_reviewer_email || "Unassigned"} {task.qa_updated_at ? ` - updated ${new Date(task.qa_updated_at).toLocaleString()}` : ""}
                      </p>
                      {task.feedback_action ? (
                        <p className="helperText">
                          Learning hook: {task.feedback_action}
                          {task.feedback_logged_at ? ` - logged ${new Date(task.feedback_logged_at).toLocaleString()}` : ""}
                        </p>
                      ) : null}
                    </form>
                  ) : null}
                </article>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
