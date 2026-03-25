"use client";

import type { Route } from "next";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "../../../components/auth-provider";
import { createJob, getErrorMessage } from "../../../lib/platform-api";

const regionOptions = ["Nairobi", "Mombasa", "Kisumu", "Eldoret", "Nyeri"];

export default function NewJobPage() {
  const router = useRouter();
  const { getIdToken } = useAuth();
  const [title, setTitle] = useState("");
  const [region, setRegion] = useState("Nairobi");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!title.trim() || !region.trim()) {
      setError("Provide both a job title and region before creating the workspace.");
      return;
    }

    setSubmitting(true);
    setError("");
    try {
      const token = await getIdToken();
      const job = await createJob({ title: title.trim(), region: region.trim() }, token);
      router.push(`/jobs/${job.id}` as Route);
      router.refresh();
    } catch (nextError) {
      setError(getErrorMessage(nextError, "The workspace could not be created right now."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="stack">
      <section className="hero">
        <span className="eyebrow">New Job</span>
        <h2 className="headline">Create a workspace and start pricing.</h2>
        <p className="lead">
          This page creates a job, captures region metadata, and sets up the workspace that will hold BOQs, artifacts,
          and future review steps.
        </p>
      </section>
      <section className="card">
        <h3>Create the workspace</h3>
        <form className="form" onSubmit={onSubmit}>
          <label>
            Job title
            <input
              name="title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="KAA terminal refurbishment pricing"
              required
            />
          </label>
          <label>
            Region
            <select name="region" value={region} onChange={(event) => setRegion(event.target.value)}>
              {regionOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <button type="submit" disabled={submitting}>
            {submitting ? "Creating..." : "Create Job"}
          </button>
          {error ? <p className="errorText">{error}</p> : null}
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
