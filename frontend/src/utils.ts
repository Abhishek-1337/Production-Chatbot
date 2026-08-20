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
