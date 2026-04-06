"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { useAuth } from "../../../components/auth-provider";
import {
  type Job,
  type PricingResult,
  getErrorMessage,
  getJob,
  getJobResults,
  priceJob,
  uploadJobFile,
} from "../../../lib/platform-api";

function formatReason(reason: string) {
  return reason.replaceAll("_", " ");
}

function decisionClass(decision: string) {
  return `decisionBadge decision-${decision || "review"}`;
}

export default function JobDetailPage() {
  const params = useParams<{ jobId: string }>();
  const jobId = params.jobId;
  const { configured, loading, user, getIdToken } = useAuth();
  const [job, setJob] = useState<Job | null>(null);
  const [pricing, setPricing] = useState<PricingResult | null>(null);
  const [loadingWorkspace, setLoadingWorkspace] = useState(true);
  const [workspaceError, setWorkspaceError] = useState("");
  const [actionError, setActionError] = useState("");
  const [notice, setNotice] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [pricingRunBusy, setPricingRunBusy] = useState(false);

  useEffect(() => {
    if (loading || (configured && !user) || !jobId) {
      return;
    }

    let cancelled = false;

    async function loadWorkspace() {
      setLoadingWorkspace(true);
      setWorkspaceError("");
      try {
        const token = await getIdToken();
        const [nextJob, nextPricing] = await Promise.all([
          getJob(jobId, token),
          getJobResults(jobId, token).catch(() => null),
        ]);
        if (!cancelled) {
          setJob(nextJob);
          setPricing(nextPricing);
        }
      } catch (error) {
        if (!cancelled) {
          setJob(null);
          setPricing(null);
          setWorkspaceError(getErrorMessage(error, "This job workspace could not be loaded right now."));
        }
      } finally {
        if (!cancelled) {
          setLoadingWorkspace(false);
        }
      }
    }

    void loadWorkspace();
    return () => {
      cancelled = true;
    };
  }, [configured, getIdToken, jobId, loading, user]);

  const latestRun = job?.runs[0] ?? null;
  const boqFile = job?.files.find((file) => file.file_type === "boq") ?? null;
  const matchedPercent = useMemo(() => {
    if (!pricing || pricing.summary.item_count <= 0) {
      return null;
    }
    return Math.round((pricing.summary.matched_count / pricing.summary.item_count) * 100);
  }, [pricing]);
  const flaggedPercent = useMemo(() => {
    if (!pricing || pricing.summary.item_count <= 0) {
      return null;
    }
    return Math.round((pricing.summary.flagged_count / pricing.summary.item_count) * 100);
  }, [pricing]);
  const reviewMessage = useMemo(() => {
    if (!pricing || flaggedPercent === null) {
      return "";
    }
    if (flaggedPercent >= 40) {
      return "This run completed, but it is review-heavy. Treat the current output as triage-first and check the flagged reasons before trusting rates.";
    }
    if (flaggedPercent >= 20) {
      return "This run produced a noticeable review queue. Low-confidence rows now carry reason badges so the team can inspect why they were held back.";
    }
    return "";
  }, [flaggedPercent, pricing]);
  const topReasons = useMemo(() => {
    if (!pricing) {
      return [];
    }
    const counts = new Map<string, number>();
    for (const item of pricing.items) {
      for (const reason of item.flag_reasons) {
        counts.set(reason, (counts.get(reason) ?? 0) + 1);
      }
    }
    return [...counts.entries()]
      .sort((left, right) => right[1] - left[1])
      .slice(0, 4);
  }, [pricing]);

  async function reloadWorkspace(nextNotice?: string) {
    if (!jobId) {
      return;
    }
    setLoadingWorkspace(true);
    setWorkspaceError("");
    setActionError("");
    if (nextNotice) {
      setNotice(nextNotice);
    }
    try {
      const token = await getIdToken();
      const [nextJob, nextPricing] = await Promise.all([
        getJob(jobId, token),
        getJobResults(jobId, token).catch(() => null),
      ]);
      setJob(nextJob);
      setPricing(nextPricing);
    } catch (error) {
      setJob(null);
      setPricing(null);
      setWorkspaceError(getErrorMessage(error, "The workspace could not be refreshed after that action."));
    } finally {
      setLoadingWorkspace(false);
    }
  }

  async function onUploadSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!jobId) {
      return;
    }
    if (!selectedFile) {
      setActionError("Choose a BOQ workbook before uploading.");
      return;
    }

    setUploading(true);
    setActionError("");
    setNotice("");
    try {
      const token = await getIdToken();
      await uploadJobFile(jobId, selectedFile, "boq", token);
      setSelectedFile(null);
      await reloadWorkspace("BOQ uploaded successfully.");
    } catch (error) {
      setActionError(getErrorMessage(error, "BOQ upload failed."));
    } finally {
      setUploading(false);
    }
  }

  async function onPriceClick() {
    if (!jobId) {
      return;
    }

    setPricingRunBusy(true);
    setActionError("");
    setNotice("");
    try {
      const token = await getIdToken();
      const response = await priceJob(jobId, token);
      setJob(response.job);
      setPricing(response.pricing);
      setNotice("Pricing run completed.");
    } catch (error) {
      setActionError(getErrorMessage(error, "Pricing could not start for this job."));
    } finally {
      setPricingRunBusy(false);
    }
  }

  if (loadingWorkspace) {
    return (
      <div className="stack">
        <section className="hero">
          <span className="eyebrow">Job Workspace</span>
          <h2 className="headline">Loading workspace...</h2>
          <p className="lead">Pulling job files, latest run details, and pricing output from the platform API.</p>
        </section>
      </div>
    );
  }

  if (workspaceError || !job) {
    return (
      <div className="stack">
        <section className="hero">
          <span className="eyebrow">Job Workspace</span>
          <h2 className="headline">This job workspace is temporarily unavailable.</h2>
          <p className="lead">
            The hosted frontend reached the API, but the workspace data did not come back cleanly. Retry from the
            dashboard instead of hitting a generic application crash.
          </p>
        </section>
        <section className="card">
          <span className="pill">Workspace Status</span>
          <p className="errorText">{workspaceError || "No workspace data is available right now."}</p>
          <div className="inlineActions">
            <button type="button" onClick={() => void reloadWorkspace()}>
              Retry workspace
            </button>
            <Link className="secondaryButton" href="/">
              Return to dashboard
            </Link>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="stack">
      <section className="hero">
        <span className="eyebrow">Job Workspace</span>
        <h2 className="headline">{job.title}</h2>
        <p className="lead">
          Region {job.region}. Upload a BOQ, trigger pricing, and review the latest line-level decisions from the API.
        </p>
      </section>

      {actionError ? (
        <section className="alertCard alertError">
          <strong>Job action failed</strong>
          <p>{actionError}</p>
        </section>
      ) : null}

      {notice ? (
        <section className="alertCard alertSuccess">
          <strong>Workspace updated</strong>
          <p>{notice}</p>
        </section>
      ) : null}

      {reviewMessage ? (
        <section className="alertCard">
          <strong>Review-first signal</strong>
          <p>{reviewMessage}</p>
        </section>
      ) : null}

      {topReasons.length > 0 ? (
        <section className="card">
          <span className="pill">Hotspots</span>
          <h3>Most common review triggers in this run</h3>
          <div className="metaGrid">
            {topReasons.map(([reason, count]) => (
              <div key={reason} className="metaRow">
                <strong>{formatReason(reason)}</strong>
                <span>{count} rows</span>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <section className="metaGrid">
        <div className="metaRow">
          <strong>Status</strong>
          <span className="statusPill">{job.status}</span>
        </div>
        <div className="metaRow">
          <strong>Files</strong>
          <span>{job.files.length}</span>
        </div>
        <div className="metaRow">
          <strong>Runs</strong>
          <span>{job.runs.length}</span>
        </div>
        <div className="metaRow">
          <strong>Updated</strong>
          <span>{new Date(job.updated_at).toLocaleString()}</span>
        </div>
      </section>

      <section className="grid">
        <article className="card">
          <span className="pill">Upload</span>
          <h3>Attach source file</h3>
          <form className="form" onSubmit={onUploadSubmit}>
            <label>
              BOQ file
              <input
                type="file"
                name="file"
                accept=".xlsx,.xlsm"
                required
                onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
              />
            </label>
            <button type="submit" disabled={uploading}>
              {uploading ? "Uploading..." : "Upload BOQ"}
            </button>
          </form>
          <p className="helperText">
            Phase 1 pricing uses the latest uploaded BOQ workbook. Tender/spec/manual uploads can be added next through
            the same job model.
          </p>
        </article>
        <article className="card">
          <span className="pill">Run</span>
          <h3>Price the uploaded BOQ</h3>
          <button type="button" onClick={() => void onPriceClick()} disabled={!boqFile || pricingRunBusy}>
            {pricingRunBusy ? "Running pricing..." : "Run Pricing"}
          </button>
          <p className="helperText">
            {boqFile
              ? `Latest BOQ: ${boqFile.filename}`
              : "Upload a BOQ workbook first, then trigger pricing from this workspace."}
          </p>
        </article>
      </section>

      <section className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
          <div>
            <span className="pill">Inputs</span>
            <h3>Uploaded files</h3>
          </div>
          <Link href="/jobs/new">Create another job</Link>
        </div>
        {job.files.length === 0 ? (
          <div className="emptyState">No files uploaded yet.</div>
        ) : (
          <div className="tableWrap">
            <table>
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Filename</th>
                  <th>Stored at</th>
                </tr>
              </thead>
              <tbody>
                {job.files.map((file) => (
                  <tr key={file.id}>
                    <td>{file.file_type}</td>
                    <td>{file.filename}</td>
                    <td className="monoText">{file.storage_uri}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="card">
        <span className="pill">Run History</span>
        <h3>Latest execution</h3>
        {latestRun ? (
          <div className="metaGrid">
            <div className="metaRow">
              <strong>Run type</strong>
              <span>{latestRun.run_type}</span>
            </div>
            <div className="metaRow">
              <strong>Status</strong>
              <span className="statusPill">{latestRun.status}</span>
            </div>
            <div className="metaRow">
              <strong>Output workbook</strong>
              <span className="monoText">{latestRun.output_storage_uri || "-"}</span>
            </div>
            <div className="metaRow">
              <strong>Audit JSON</strong>
              <span className="monoText">{latestRun.audit_storage_uri || "-"}</span>
            </div>
          </div>
        ) : (
          <div className="emptyState">No runs yet. This panel will show the latest workbook and audit artifact URIs.</div>
        )}
      </section>

      <section className="card">
        <span className="pill">Pricing Output</span>
        <h3>Latest pricing summary</h3>
        {pricing ? (
          <>
            <div className="triageLegend">
              <div className="triageLegendItem">`matched` means the row cleared pricing thresholds.</div>
              <div className="triageLegendItem">`review` means the engine found a candidate but wants QS attention.</div>
              <div className="triageLegendItem">`unmatched` means price manually or improve the library first.</div>
            </div>
            <div className="metaGrid">
              <div className="metaRow">
                <strong>Total cost</strong>
                <span>
                  {pricing.summary.currency} {pricing.summary.total_cost.toLocaleString()}
                </span>
              </div>
              <div className="metaRow">
                <strong>Processed</strong>
                <span>{pricing.summary.item_count}</span>
              </div>
              <div className="metaRow">
                <strong>Matched</strong>
                <span>{pricing.summary.matched_count}</span>
              </div>
              <div className="metaRow">
                <strong>Flagged</strong>
                <span>{pricing.summary.flagged_count}</span>
              </div>
              <div className="metaRow">
                <strong>Matched rate</strong>
                <span>{matchedPercent === null ? "-" : `${matchedPercent}%`}</span>
              </div>
              <div className="metaRow">
                <strong>Review pressure</strong>
                <span>{flaggedPercent === null ? "-" : `${flaggedPercent}%`}</span>
              </div>
            </div>
            <div className="tableWrap">
              <table>
                <thead>
                  <tr>
                    <th>Description</th>
                    <th>Unit</th>
                    <th>Decision</th>
                    <th>Match</th>
                    <th>Rate</th>
                    <th>Amount</th>
                    <th>Triage</th>
                  </tr>
                </thead>
                <tbody>
                  {pricing.items.slice(0, 20).map((item, index) => (
                    <tr key={`${item.description}-${index}`} className="rowMuted">
                      <td>{item.description}</td>
                      <td>{item.unit || "-"}</td>
                      <td>
                        <span className={decisionClass(item.decision)}>{item.decision}</span>
                      </td>
                      <td>{item.matched_description || "-"}</td>
                      <td>{item.rate ?? "-"}</td>
                      <td>{item.amount ?? "-"}</td>
                      <td className="triageCell">
                        <div className="triageStack">
                          <span className={`confidenceBadge confidence-${item.confidence_band}`}>{item.confidence_band}</span>
                          <div className="triageScore">Score {item.confidence_score.toFixed(2)}</div>
                        </div>
                        {item.flag_reasons.length > 0 ? (
                          <div className="reasonList">
                            {item.flag_reasons.map((reason) => (
                              <span key={reason} className="reasonBadge">
                                {formatReason(reason)}
                              </span>
                            ))}
                          </div>
                        ) : null}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="helperText">
              Showing the first 20 priced rows. Later iterations should add full filtering for matched, review, and
              unmatched decisions.
            </p>
          </>
        ) : (
          <div className="emptyState">No pricing run yet. Upload a BOQ and run pricing to populate this panel.</div>
        )}
      </section>
    </div>
  );
}
