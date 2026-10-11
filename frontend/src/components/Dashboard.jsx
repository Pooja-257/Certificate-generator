import { useEffect, useState } from "react";
import { api, isFinished } from "../api.js";
import StatusBadge from "./StatusBadge.jsx";
import ProgressBar from "./ProgressBar.jsx";

const formatWhen = (iso) =>
  new Date(iso).toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

export default function Dashboard() {
  const [jobs, setJobs] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let timer;
    let cancelled = false;
    async function load() {
      try {
        const data = await api.listJobs();
        if (cancelled) return;
        setJobs(data);
        setError("");
        // Keep refreshing only while something is still running.
        if (data.some((job) => !isFinished(job.status))) timer = setTimeout(load, 1500);
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }
    load();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, []);

  return (
    <section>
      <div className="page-head">
        <h1>Your batches</h1>
        <p className="lede">Every batch turns a list of people into individual PDF certificates.</p>
      </div>

      {error && <p className="notice notice-error">{error}</p>}
      {jobs === null && !error && <p className="muted">Loading batches…</p>}

      {jobs?.length === 0 && (
        <div className="empty">
          <h2>No batches yet</h2>
          <p>Add a few recipients and the PDFs are generated for you in seconds.</p>
          <a href="#/new" className="btn btn-primary">Create your first batch</a>
        </div>
      )}

      {jobs?.length > 0 && (
        <ul className="job-list">
          {jobs.map((job) => (
            <li key={job.job_id}>
              <a href={`#/jobs/${job.job_id}`} className="job-row">
                <div className="job-main">
                  <h2>{job.certificate_title}</h2>
                  <p>{job.event_name}, {job.organization_name}</p>
                  <p className="muted small">Batch {job.job_id} created {formatWhen(job.created_at)}</p>
                </div>
                <div className="job-progress">
                  <ProgressBar percent={job.progress_percentage} failed={job.failed} total={job.total} />
                  <p className="small">
                    <strong>{job.successful}</strong> of {job.total} issued
                    {job.failed > 0 && <span className="text-bad"> and {job.failed} failed</span>}
                  </p>
                </div>
                <StatusBadge status={job.status} />
              </a>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
