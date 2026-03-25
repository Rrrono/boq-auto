import { redirect } from "next/navigation";

import { createJob } from "../../../lib/platform-api";


async function createJobAction(formData: FormData) {
  "use server";

  const title = String(formData.get("title") || "").trim();
  const region = String(formData.get("region") || "").trim();
  if (!title || !region) {
    return;
  }
  const job = await createJob({ title, region });
  redirect(`/jobs/${job.id}`);
}


export default function NewJobPage() {
  return (
    <div className="stack">
      <section className="hero">
        <span className="eyebrow">New Job</span>
        <h2 className="headline">Create a workspace and start pricing.</h2>
        <p className="lead">
          This page will create a job, collect region and project metadata, and upload BOQs, tenders, manuals, and specs
          into Cloud Storage before the review workflow starts.
        </p>
      </section>
      <section className="card">
        <h3>Create the workspace</h3>
        <form className="form" action={createJobAction}>
          <label>
            Job title
            <input name="title" placeholder="KAA terminal refurbishment pricing" required />
          </label>
          <label>
            Region
            <select name="region" defaultValue="Nairobi">
              <option value="Nairobi">Nairobi</option>
              <option value="Mombasa">Mombasa</option>
              <option value="Kisumu">Kisumu</option>
              <option value="Eldoret">Eldoret</option>
              <option value="Nyeri">Nyeri</option>
            </select>
          </label>
          <button type="submit">Create Job</button>
        </form>
      </section>
      <section className="grid">
        <article className="card">
          <span className="pill">Intake</span>
          <h3>What comes into a job</h3>
          <p>
            Start with the BOQ workbook, then add supporting tenders, specifications, manuals, and other source files as
            the review flow expands.
          </p>
        </article>
        <article className="card">
          <span className="pill">Outcome</span>
          <h3>What the team gets back</h3>
          <p>
            A tracked workspace with pricing runs, storage-backed artifacts, and a review surface for flagged lines and
            future knowledge promotion.
          </p>
        </article>
      </section>
    </div>
  );
}
