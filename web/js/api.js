// Thin fetch wrapper. Every error from the server has the shape
// {error: {code, message, field, details}}; it is rethrown as ApiError so the
// views can show the exact message (and field) instead of a generic failure.

export class ApiError extends Error {
  constructor(status, body) {
    const err = (body && body.error) || {};
    super(err.message || `Request failed (HTTP ${status})`);
    this.status = status;
    this.code = err.code || "http_error";
    this.field = err.field || null;
    this.details = err.details || null;
  }
}

async function handle(res) {
  if (res.status === 204) return null;
  let body = null;
  try { body = await res.json(); } catch { /* non-JSON body */ }
  if (!res.ok) throw new ApiError(res.status, body);
  return body;
}

export async function get(path) {
  let res;
  try { res = await fetch(path, { headers: { Accept: "application/json" } }); }
  catch { throw new ApiError(0, { error: { code: "offline", message: "Cannot reach the server. Is `python run_app.py` still running?" } }); }
  return handle(res);
}

export async function post(path, body) {
  let res;
  try {
    res = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" },
                              body: JSON.stringify(body) });
  } catch { throw new ApiError(0, { error: { code: "offline", message: "Cannot reach the server. Is `python run_app.py` still running?" } }); }
  return handle(res);
}

export async function del(path) {
  const res = await fetch(path, { method: "DELETE" });
  return handle(res);
}

export async function upload(path, file) {
  const form = new FormData();
  form.append("file", file);
  let res;
  try { res = await fetch(path, { method: "POST", body: form }); }
  catch { throw new ApiError(0, { error: { code: "offline", message: "Cannot reach the server." } }); }
  return handle(res);
}

let examplesCache = null;
export async function examples() {
  if (!examplesCache) examplesCache = (await get("/api/examples")).examples;
  return examplesCache;
}
export async function example(id) {
  return (await get(`/api/examples/${encodeURIComponent(id)}`));
}
