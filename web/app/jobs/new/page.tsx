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
        <h3>Planned fields</h3>
        <p>Project title, region, client, trade scope, and initial file uploads.</p>
      </section>
    </div>
  );
}
