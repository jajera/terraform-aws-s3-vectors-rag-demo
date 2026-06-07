async function apiRequest(path, options = {}) {
  const token = await getIdToken();
  const response = await fetch(`${window.APP_CONFIG.apiUrl}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(options.headers || {}),
    },
  });

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.error || `Request failed (${response.status})`);
  }
  return body;
}

function getStatus() {
  return apiRequest("/status");
}

function postQuery(question) {
  return apiRequest("/query", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}

function postIngest() {
  return apiRequest("/ingest", { method: "POST" });
}
