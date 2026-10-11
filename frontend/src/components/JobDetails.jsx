import { useEffect, useState } from "react";
import { api, isFinished } from "../api.js";
import StatusBadge from "./StatusBadge.jsx";
import ProgressBar from "./ProgressBar.jsx";

export default function JobDetails({ jobId }) {
  const [job, setJob] = useState(null);
  const [certs, setCerts] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let timer;
    let cancelled = false;
    async function load() {
      try {
        const [jobData, certData] = await Promise.all([api.getJob(jobId), api.getCertificates(jobId)]);
        if (cancelled) return;
        setJob(jobData);
        setCerts(certData.certificates);
        if (!isFinished(jobData.status)) timer = setTimeout(load, 1000);
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }
    load();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [jobId]);

  if (error) return <p className="notice notice-error">{error} <a href="#/">Back to batches</a></p>;
  if (!job) return <p className="muted">Loading batch…</p>;

  return (
    <section>
      <a href="#/" className="back">All batches</a>
      <div className="page-head job-head">
        <div>
          <h1>{job.certificate_title}</h1>
          <p className="lede">{job.event_name}, {job.organization_name}</p>
        </div>
        <StatusBadge status={job.status} />
      </div>

      <div className="panel">
        <ProgressBar percent={job.progress_percentage} failed={job.failed} total={job.total} />
        <div className="figures">
          <div><span className="figure">{job.progress_percentage}%</span><span className="figure-label">complete</span></div>
          <div><span className="figure">{job.total}</span><span className="figure-label">recipients</span></div>
          <div><span className="figure text-ok">{job.successful}</span><span className="figure-label">issued</span></div>
          <div><span className={`figure ${job.failed ? "text-bad" : ""}`}>{job.failed}</span><span className="figure-label">failed</span></div>
        </div>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>Name</th><th>Email</th><th>Course</th><th>Status</th><th>Certificate</th></tr>
          </thead>
          <tbody>
            {certs.map((c) => (
              <tr key={c.id}>
                <td data-label="Name">{c.recipient_name}</td>
                <td data-label="Email">{c.recipient_email}</td>
                <td data-label="Course">{c.course}</td>
                <td data-label="Status"><StatusBadge status={c.status} /></td>
                <td data-label="Certificate">
                  {c.download_url && (
                    <a className="link" href={api.downloadUrl(c.download_url)} target="_blank" rel="noreferrer">
                      Download PDF
                    </a>
                  )}
                  {c.error_message && <span className="text-bad small">{c.error_message}</span>}
                  {!c.download_url && !c.error_message && <span className="muted small">Waiting</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
