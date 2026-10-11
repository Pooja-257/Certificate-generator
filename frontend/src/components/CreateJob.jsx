import { useState } from "react";
import { api } from "../api.js";
import CertificatePreview from "./CertificatePreview.jsx";

const emptyRecipient = () => ({ name: "", email: "", course: "" });
const today = () => new Date().toISOString().slice(0, 10);

const SAMPLE = {
  certificate_title: "Certificate of Participation",
  event_name: "AI Workshop 2026",
  organization_name: "ABC Organization",
  issue_date: "2026-10-08",
  recipients: [
    { name: "John Doe", email: "john@example.com", course: "Artificial Intelligence" },
    { name: "Jane Smith", email: "jane@example.com", course: "Artificial Intelligence" },
    { name: "Priya Sharma", email: "priya@example.com", course: "Machine Learning" },
    { name: "José Müller", email: "jose@example.com", course: "Data Science" },
    { name: "Amira Hassan", email: "amira@example.com", course: "Artificial Intelligence" },
    { name: "李雷 (Li Lei)", email: "lilei@example.com", course: "Machine Learning" },
  ],
};

// "Name, email, course" per line (commas or tabs, so rows can be pasted from a spreadsheet).
function parsePasted(text) {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [name = "", email = "", ...rest] = line.split(/\t|,/).map((p) => p.trim());
      return { name, email, course: rest.join(", ") };
    });
}

export default function CreateJob() {
  const [form, setForm] = useState({
    certificate_title: "Certificate of Participation",
    event_name: "",
    organization_name: "",
    issue_date: today(),
  });
  const [recipients, setRecipients] = useState([emptyRecipient()]);
  const [pasteOpen, setPasteOpen] = useState(false);
  const [pasteText, setPasteText] = useState("");
  const [errors, setErrors] = useState([]);
  const [submitting, setSubmitting] = useState(false);

  const setField = (key) => (e) => setForm({ ...form, [key]: e.target.value });
  const setRecipient = (index, key) => (e) =>
    setRecipients(recipients.map((r, i) => (i === index ? { ...r, [key]: e.target.value } : r)));
  const removeRecipient = (index) =>
    setRecipients(recipients.length === 1 ? [emptyRecipient()] : recipients.filter((_, i) => i !== index));

  const loadSample = () => {
    const { recipients: sampleRecipients, ...fields } = SAMPLE;
    setForm(fields);
    setRecipients(sampleRecipients);
    setErrors([]);
  };

  const addPasted = () => {
    const parsed = parsePasted(pasteText);
    if (parsed.length === 0) return;
    const kept = recipients.filter((r) => r.name || r.email || r.course);
    setRecipients([...kept, ...parsed]);
    setPasteText("");
    setPasteOpen(false);
  };

  async function submit(e) {
    e.preventDefault();
    setErrors([]);
    setSubmitting(true);
    try {
      const filled = recipients.filter((r) => r.name || r.email || r.course);
      const job = await api.createJob({ ...form, recipients: filled });
      window.location.hash = `#/jobs/${job.job_id}`;
    } catch (err) {
      setErrors(err.details?.length ? err.details.map((d) => friendly(d)) : [err.message]);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } finally {
      setSubmitting(false);
    }
  }

  const filledCount = recipients.filter((r) => r.name || r.email || r.course).length;

  return (
    <section>
      <a href="#/" className="back">All batches</a>
      <div className="page-head">
        <h1>New batch</h1>
        <p className="lede">Fill in the details once. Each recipient gets their own PDF.</p>
      </div>

      <div className="create-grid">
        <form onSubmit={submit} className="stack">
          {errors.length > 0 && (
            <div className="notice notice-error" role="alert">
              <strong>Fix these before generating:</strong>
              <ul>{errors.map((m, i) => <li key={i}>{m}</li>)}</ul>
            </div>
          )}

          <fieldset className="panel">
            <legend>Certificate</legend>
            <label>Certificate title
              <input value={form.certificate_title} onChange={setField("certificate_title")} maxLength={100} required />
            </label>
            <div className="two">
              <label>Event name
                <input value={form.event_name} onChange={setField("event_name")} maxLength={150} required placeholder="AI Workshop 2026" />
              </label>
              <label>Organization name
                <input value={form.organization_name} onChange={setField("organization_name")} maxLength={150} required placeholder="ABC Organization" />
              </label>
            </div>
            <label className="narrow">Issue date
              <input type="date" value={form.issue_date} onChange={setField("issue_date")} required />
            </label>
          </fieldset>

          <fieldset className="panel">
            <legend>Recipients</legend>
            <div className="recipients">
              {recipients.map((r, i) => (
                <div className="recipient" key={i}>
                  <input aria-label={`Recipient ${i + 1} name`} placeholder="Full name" value={r.name} onChange={setRecipient(i, "name")} maxLength={100} />
                  <input aria-label={`Recipient ${i + 1} email`} placeholder="Email" type="email" value={r.email} onChange={setRecipient(i, "email")} />
                  <input aria-label={`Recipient ${i + 1} course`} placeholder="Course" value={r.course} onChange={setRecipient(i, "course")} maxLength={150} />
                  <button type="button" className="icon-btn" onClick={() => removeRecipient(i)} aria-label={`Remove recipient ${i + 1}`}>×</button>
                </div>
              ))}
            </div>

            <div className="row">
              <button type="button" className="btn btn-quiet" onClick={() => setRecipients([...recipients, emptyRecipient()])}>Add recipient</button>
              <button type="button" className="btn btn-quiet" onClick={() => setPasteOpen(!pasteOpen)}>Paste a list</button>
              <button type="button" className="btn btn-quiet" onClick={loadSample}>Load sample batch</button>
            </div>

            {pasteOpen && (
              <div className="paste">
                <label>One person per line: name, email, course
                  <textarea rows={5} value={pasteText} onChange={(e) => setPasteText(e.target.value)}
                    placeholder={"Priya Sharma, priya@example.com, Machine Learning\nJohn Doe, john@example.com, Data Science"} />
                </label>
                <button type="button" className="btn btn-primary" onClick={addPasted}>Add these people</button>
              </div>
            )}
          </fieldset>

          <div className="row submit-row">
            <button className="btn btn-primary btn-large" disabled={submitting || filledCount === 0}>
              {submitting ? "Generating…" : `Generate ${filledCount || ""} certificate${filledCount === 1 ? "" : "s"}`.replace("  ", " ")}
            </button>
          </div>
        </form>

        <aside className="preview-col">
          <CertificatePreview values={form} recipient={recipients.find((r) => r.name || r.course)} />
        </aside>
      </div>
    </section>
  );
}

function friendly({ field, message }) {
  const m = field.match(/^recipients\.(\d+)\.(\w+)$/);
  const where = m ? `Recipient ${Number(m[1]) + 1}, ${m[2]}` : field.replaceAll("_", " ") || "Request";
  return `${where}: ${message}`;
}
