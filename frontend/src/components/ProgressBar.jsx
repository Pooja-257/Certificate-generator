export default function ProgressBar({ percent, failed = 0, total = 1 }) {
  const failedPercent = Math.floor((failed * 100) / Math.max(total, 1));
  return (
    <div
      className="progress"
      role="progressbar"
      aria-valuenow={percent}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label="Generation progress"
    >
      <div className="progress-ok" style={{ width: `${Math.max(percent - failedPercent, 0)}%` }} />
      <div className="progress-bad" style={{ width: `${failedPercent}%` }} />
    </div>
  );
}
