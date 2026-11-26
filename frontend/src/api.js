const API_PREFIX = "/api/v1";

async function request(path, options = {}) {
  const response = await fetch(path, options);
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const detail = typeof payload === "object"
      ? payload.detail || payload.message || JSON.stringify(payload)
      : payload;
    throw new Error(detail || `Request failed (${response.status})`);
  }

  return payload;
}

export const api = {
  health: () => request("/health"),
  databaseHealth: () => request(`${API_PREFIX}/health/db`),
  info: () => request(`${API_PREFIX}/info`),
  documents: (limit = 100, offset = 0) =>
    request(`${API_PREFIX}/documents?limit=${limit}&offset=${offset}`),
  upload: (file) => {
    const form = new FormData();
    form.append("file", file);
    return request(`${API_PREFIX}/documents/upload`, {
      method: "POST",
      body: form
    });
  },
  deleteDocument: (id) =>
    request(`${API_PREFIX}/documents/${encodeURIComponent(id)}`, {
      method: "DELETE"
    }),
  chat: (body) =>
    request(`${API_PREFIX}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }),
  history: (id) =>
    request(`${API_PREFIX}/chat/history/${encodeURIComponent(id)}`),
  approvals: () => request(`${API_PREFIX}/approvals`),
  reviewApproval: (id, body) =>
    request(`${API_PREFIX}/approvals/${encodeURIComponent(id)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    })
};
