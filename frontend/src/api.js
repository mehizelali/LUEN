const API_BASE = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8100";

function authHeaders() {
  const token = localStorage.getItem("token");
  return token
    ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }
    : { "Content-Type": "application/json" };
}

async function request(path, init) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...authHeaders(), ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return undefined;
  return res.json();
}

export const api = {
  register: (email, name, password) =>
    request("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, name, password }),
    }),
  login: (email, password) =>
    request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request("/api/auth/me"),
  listOrgs: () => request("/api/orgs"),
  createOrg: (name, slug) =>
    request("/api/orgs", { method: "POST", body: JSON.stringify({ name, slug }) }),
  dashboard: (orgId) => request(`/api/orgs/${orgId}/dashboard`),
  adminDashboard: (orgId) => request(`/api/orgs/${orgId}/admin-dashboard`),
  listMembers: (orgId) => request(`/api/orgs/${orgId}/members`),
  listProjects: (orgId) => request(`/api/orgs/${orgId}/projects`),
  createProject: (orgId, name, key, description) =>
    request(`/api/orgs/${orgId}/projects`, {
      method: "POST",
      body: JSON.stringify({ name, key, description }),
    }),
  getProject: (projectId) => request(`/api/projects/${projectId}`),
  listStatuses: (projectId) => request(`/api/projects/${projectId}/statuses`),
  listWorkItems: (projectId, q) =>
    request(
      `/api/projects/${projectId}/work-items${q ? `?q=${encodeURIComponent(q)}` : ""}`,
    ),
  createWorkItem: (projectId, data) =>
    request(`/api/projects/${projectId}/work-items`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getWorkItem: (id) => request(`/api/work-items/${id}`),
  updateWorkItem: (id, data) =>
    request(`/api/work-items/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  listComments: (id) => request(`/api/work-items/${id}/comments`),
  createComment: (id, body) =>
    request(`/api/work-items/${id}/comments`, {
      method: "POST",
      body: JSON.stringify({ body }),
    }),
};
