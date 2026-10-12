const apiBase = import.meta.env.VITE_API_BASE_URL || `http://${window.location.hostname}:8000`;

export async function fetchAnalysis(input: string[]) {
  const response = await fetch(`${apiBase}/analysis/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ meeting_records: input }),
  });
  if (!response.ok) {
    throw new Error(`Request failed with ${response.status}`);
  }
  return response.json();
}
