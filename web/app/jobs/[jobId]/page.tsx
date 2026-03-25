import Link from "next/link";
import { redirect } from "next/navigation";

import { getJob, getJobResults, priceJob, uploadJobFile } from "../../../lib/platform-api";


async function uploadBoqAction(formData: FormData) {
  "use server";

  const jobId = String(formData.get("jobId") || "");
  const file = formData.get("file");
  if (!jobId || !(file instanceof File) || !file.size) {
    return;
  }
  await uploadJobFile(jobId, file, "boq");
  redirect(`/jobs/${jobId}`);
}


async function priceBoqAction(formData: FormData) {
  "use server";

  const jobId = String(formData.get("jobId") || "");
  if (!jobId) {
    return;
  }
  await priceJob(jobId);
  redirect(`/jobs/${jobId}`);
}


export default async function JobDetailPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await params;
  const job = await getJob(jobId);
  const pricing = await getJobResults(jobId).catch(() => null);
  const latestRun = job.runs[0] ?? null;
  const boqFile = job.files.find((file) => file.file_type === "boq") ?? null;
  const matchedPercent =
    pricing && pricing.summary.item_count > 0
      ? Math.round((pricing.summary.matched_count / pricing.summary.item_count) * 100)
      : null;
  const flaggedPercent =
    pricing && pricing.summary.item_count > 0
      ? Math.round((pricing.summary.flagged_count / pricing.summary.item_count) * 100)
      : null;

  return (
    <div className="stack">
      <section className="hero">
        <span className="eyebrow">Job Workspace</span>
        <h2 className="headline">{job.title}</h2>
        <p className="lead">
          Region {job.region}. Upload a BOQ, trigger pricing, and review the latest line-level decisions from the API.
        </p>
      </section>

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
          <form className="form" action={uploadBoqAction}>
            <input type="hidden" name="jobId" value={job.id} />
            <label>
              BOQ file
              <input type="file" name="file" accept=".xlsx,.xlsm" required />
            </label>
            <button type="submit">Upload BOQ</button>
          </form>
          <p className="helperText">
            Phase 1 pricing uses the latest uploaded BOQ workbook. Tender/spec/manual uploads can be added next through
            the same job model.
          </p>
        </article>
        <article className="card">
          <span className="pill">Run</span>
          <h3>Price the uploaded BOQ</h3>
          <form className="form" action={priceBoqAction}>
            <input type="hidden" name="jobId" value={job.id} />
            <button type="submit" disabled={!boqFile}>
              Run Pricing
            </button>
          </form>
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
          <>
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
          </>
        ) : (
          <div className="emptyState">No runs yet. This panel will show the latest workbook and audit artifact URIs.</div>
        )}
      </section>

      <section className="card">
        <span className="pill">Pricing Output</span>
        <h3>Latest pricing summary</h3>
        {pricing ? (
          <>
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
                    <th>Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {pricing.items.slice(0, 20).map((item, index) => (
                    <tr key={`${item.description}-${index}`}>
                      <td>{item.description}</td>
                      <td>{item.unit || "-"}</td>
                      <td>{item.decision}</td>
                      <td>{item.matched_description || "-"}</td>
                      <td>{item.rate ?? "-"}</td>
                      <td>{item.amount ?? "-"}</td>
                      <td>{item.confidence_score.toFixed(2)}</td>
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
