export function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

export function formatDate(date: string) {
  const value = new Date(date);
  const today = new Date();
  return value.toDateString() === today.toDateString()
    ? value.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })
    : value.toLocaleDateString([], { month: "short", day: "numeric" });
}

export function getConversationIdFromUrl() {
  const match = window.location.pathname.match(/^\/conversations\/([^/]+)\/?$/);
  return match ? decodeURIComponent(match[1]) : null;
}

export function updateConversationUrl(id: string | null, replace = false) {
  const url = new URL(window.location.href);
  url.pathname = id ? `/conversations/${encodeURIComponent(id)}` : "/";
  url.search = "";

  window.history[replace ? "replaceState" : "pushState"]({}, "", url);
}
