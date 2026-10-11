// Thin wrapper around fetch. Errors from the backend look like {error: {code, message, details}}.
const BASE = import.meta.env.VITE_API_URL ?? "";

export class ApiError extends Error {
  constructor(message, details = []) {
    super(message);
    this.details = details;
  }
}

async function request(path, options) {
  let response;
  try {
    response = await fetch(`${BASE}/api${path}`, options);
  } catch {
    throw new ApiError("Can't reach the server. Is the backend running on port 8000?");
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(body?.error?.message ?? "Something went wrong.", body?.error?.details ?? []);
  }
  return body;
}

export const api = {
  listJobs: () => request("/jobs?limit=30"),
  getJob: (id) => request(`/jobs/${id}`),
  getCertificates: (id) => request(`/jobs/${id}/certificates`),
  createJob: (payload) =>
    request("/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  downloadUrl: (path) => `${BASE}${path}`,
};

export const isFinished = (status) => ["COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED"].includes(status);
