import { useEffect, useState } from "react";

import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  BarChart,
  Bar,
  Legend,
} from "recharts";
import { Link } from "react-router-dom";
import { API_URL } from "../config";

const TOKEN_KEY = "rag-token";

type DailyRow = {
  date: string;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  query_count: number;
};
type TopUser = {
  user_id: string;
  email: string;
  name: string;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  query_count: number;
};
type Summary = {
  total_tokens: number;
  today_tokens: number;
  last_7d_tokens: number;
  last_30d_tokens: number;
  active_users_30d: number;
};

function getToken() {
  return localStorage.getItem(TOKEN_KEY) ?? "";
}

function formatDate(d: Date) {
  return d.toISOString().slice(0, 10);
}

export default function AdminDashboard() {
  const [start, setStart] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 29);
    return formatDate(d);
  });
  const [end, setEnd] = useState(() => formatDate(new Date()));
  const [source, setSource] = useState<"all" | "llm" | "embedding" | "summary">("all");
  const [daily, setDaily] = useState<DailyRow[]>([]);
  const [topUsers, setTopUsers] = useState<TopUser[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [topPerDay, setTopPerDay] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const token = getToken();

  const fetchAll = async () => {
    setLoading(true);
    setError("");
    try {
      const qs = `start=${start}&end=${end}&source=${source}`;
      const d1 = await fetch(`${API_URL}/admin/token-usage/daily?${qs}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!d1.ok) {
        const j = await d1.json().catch(() => null);
        throw new Error(j?.detail ?? `Daily failed ${d1.status}`);
      }
      const j1 = await d1.json();
      setDaily(j1.data);

      const d2 = await fetch(`${API_URL}/admin/token-usage/top-users?${qs}&limit=10`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!d2.ok) throw new Error("Top users failed");
      const j2 = await d2.json();
      setTopUsers(j2.data);

      const d3 = await fetch(`${API_URL}/admin/token-usage/summary?source=${source}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (d3.ok) {
        const j3 = await d3.json();
        setSummary(j3);
      }

      const d4 = await fetch(`${API_URL}/admin/token-usage/top-per-day?${qs}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (d4.ok) {
        const j4 = await d4.json();
        setTopPerDay(j4.data);
      }
    } catch (e: any) {
      setError(e.message ?? "Failed to load");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="min-h-svh bg-[var(--paper)] text-[var(--ink)] p-6">
      <div className="mx-auto max-w-[1100px]">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
          <h1 className="text-2xl font-semibold">Admin — Token Usage</h1>
          <Link to="/" className="text-sm text-[var(--muted)] hover:text-[var(--ink)] underline">
            Back to chat
          </Link>
        </div>

        <div className="flex flex-wrap gap-3 items-end mb-6 bg-white/60 dark:bg-[#1a2a30]/60 p-4 rounded-xl border border-[var(--line)]">
          <label className="flex flex-col gap-1 text-xs">
            <span className="font-medium">Start</span>
            <input type="date" value={start} onChange={(e) => setStart(e.target.value)} className="rounded border border-[var(--line)] px-2 py-1 bg-transparent" />
          </label>
          <label className="flex flex-col gap-1 text-xs">
            <span className="font-medium">End</span>
            <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} className="rounded border border-[var(--line)] px-2 py-1 bg-transparent" />
          </label>
          <label className="flex flex-col gap-1 text-xs">
            <span className="font-medium">Source</span>
            <select value={source} onChange={(e) => setSource(e.target.value as any)} className="rounded border border-[var(--line)] px-2 py-1 bg-transparent">
              <option value="all">All (LLM + Embedding + Summary)</option>
              <option value="llm">LLM</option>
              <option value="embedding">Embedding</option>
              <option value="summary">Summary</option>
            </select>
          </label>
          <button onClick={() => void fetchAll()} disabled={loading} className="ml-auto rounded bg-[#7eb587] text-white px-4 py-2 text-sm disabled:opacity-60">
            {loading ? "Loading..." : "Apply"}
          </button>
        </div>

        {error && <div className="mb-4 rounded bg-red-50 border border-red-200 text-red-700 px-4 py-2 text-sm">{error}</div>}

        {summary && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="rounded-xl border border-[var(--line)] bg-white dark:bg-[#1e323a] p-4">
              <div className="text-xs text-[var(--muted)]">Total tokens</div>
              <div className="text-xl font-semibold">{summary.total_tokens.toLocaleString()}</div>
              <div className="text-[11px] text-[var(--muted)]">All time ({source})</div>
            </div>
            <div className="rounded-xl border border-[var(--line)] bg-white dark:bg-[#1e323a] p-4">
              <div className="text-xs text-[var(--muted)]">Today</div>
              <div className="text-xl font-semibold">{summary.today_tokens.toLocaleString()}</div>
            </div>
            <div className="rounded-xl border border-[var(--line)] bg-white dark:bg-[#1e323a] p-4">
              <div className="text-xs text-[var(--muted)]">Last 7 days</div>
              <div className="text-xl font-semibold">{summary.last_7d_tokens.toLocaleString()}</div>
            </div>
            <div className="rounded-xl border border-[var(--line)] bg-white dark:bg-[#1e323a] p-4">
              <div className="text-xs text-[var(--muted)]">Last 30 days / Active users</div>
              <div className="text-xl font-semibold">{summary.last_30d_tokens.toLocaleString()} <span className="text-sm font-normal text-[var(--muted)]">/ {summary.active_users_30d} users</span></div>
            </div>
          </div>
        )}

        <div className="rounded-xl border border-[var(--line)] bg-white dark:bg-[#1e323a] p-4 mb-6">
          <h2 className="text-sm font-semibold mb-3">Tokens per day</h2>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={daily} margin={{ left: 10, right: 10, top: 10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Area type="monotone" dataKey="total_tokens" name="Total" stroke="#7eb587" fill="#7eb587" fillOpacity={0.3} />
                <Area type="monotone" dataKey="prompt_tokens" name="Prompt" stroke="#6b8db5" fill="#6b8db5" fillOpacity={0.15} />
                <Area type="monotone" dataKey="completion_tokens" name="Completion" stroke="#d9a05b" fill="#d9a05b" fillOpacity={0.15} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-2 text-[11px] text-[var(--muted)]">Daily totals grouped by UTC date_trunc. Switch source filter to see embedding vs LLM breakdown.</div>
        </div>

        <div className="grid md:grid-cols-2 gap-6 mb-6">
          <div className="rounded-xl border border-[var(--line)] bg-white dark:bg-[#1e323a] p-4">
            <h2 className="text-sm font-semibold mb-3">Top consumers (selected range)</h2>
            <div className="h-[320px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={topUsers} layout="vertical" margin={{ left: 20, right: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="email" tick={{ fontSize: 11 }} width={140} />
                  <Tooltip />
                  <Bar dataKey="total_tokens" name="Tokens" fill="#7eb587" />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-3 overflow-auto max-h-[260px] border rounded border-[var(--line)]">
              <table className="w-full text-xs">
                <thead className="bg-[#f4f4f0] dark:bg-[#22343c] sticky top-0">
                  <tr>
                    <th className="text-left p-2">#</th>
                    <th className="text-left p-2">User</th>
                    <th className="text-right p-2">Tokens</th>
                    <th className="text-right p-2">Queries</th>
                  </tr>
                </thead>
                <tbody>
                  {topUsers.map((u, i) => (
                    <tr key={u.user_id} className="border-t border-[var(--line)]">
                      <td className="p-2">{i + 1}</td>
                      <td className="p-2">
                        <div className="font-medium">{u.name}</div>
                        <div className="text-[11px] text-[var(--muted)]">{u.email}</div>
                      </td>
                      <td className="p-2 text-right font-mono">{u.total_tokens.toLocaleString()}</td>
                      <td className="p-2 text-right">{u.query_count}</td>
                    </tr>
                  ))}
                  {topUsers.length === 0 && (
                    <tr>
                      <td colSpan={4} className="p-4 text-center text-[var(--muted)]">
                        No data in range — send a query to generate usage.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="rounded-xl border border-[var(--line)] bg-white dark:bg-[#1e323a] p-4">
            <h2 className="text-sm font-semibold mb-3">Who consumed most per day</h2>
            <div className="overflow-auto max-h-[620px] border rounded border-[var(--line)]">
              <table className="w-full text-xs">
                <thead className="bg-[#f4f4f0] dark:bg-[#22343c] sticky top-0">
                  <tr>
                    <th className="text-left p-2">Date</th>
                    <th className="text-left p-2">Top user</th>
                    <th className="text-right p-2">Tokens</th>
                  </tr>
                </thead>
                <tbody>
                  {topPerDay.map((r) => (
                    <tr key={r.date} className="border-t border-[var(--line)]">
                      <td className="p-2 font-mono">{r.date}</td>
                      <td className="p-2">{r.email ? `${r.name} (${r.email})` : <span className="text-[var(--muted)]">—</span>}</td>
                      <td className="p-2 text-right font-mono">{r.total_tokens.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
