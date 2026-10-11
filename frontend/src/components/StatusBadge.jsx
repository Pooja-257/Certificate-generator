const LABELS = {
  PENDING: "Queued",
  PROCESSING: "Generating",
  COMPLETED: "Done",
  COMPLETED_WITH_ERRORS: "Done with errors",
  FAILED: "Failed",
  SUCCESS: "Ready",
};

export default function StatusBadge({ status }) {
  return <span className={`badge badge-${status.toLowerCase()}`}>{LABELS[status] ?? status}</span>;
}
