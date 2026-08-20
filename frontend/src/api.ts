import type { Conversation, User } from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function createApi(token: string) {
  async function request(path: string, options: RequestInit = {}) {
    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        ...(options.body instanceof FormData
          ? {}
          : { "Content-Type": "application/json" }),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new ApiError(
        payload?.detail ?? "Something went wrong",
        response.status,
      );
    }

    return response;
  }

  return {
    async getUser() {
      return (await request("/auth/me")).json() as Promise<User>;
    },
    async getConversations() {
      return (await request("/conversations")).json() as Promise<
        Conversation[]
      >;
    },
    async getConversation(id: string) {
      return (
        await request(`/conversations/${id}`)
      ).json() as Promise<Conversation>;
    },
    async upload(file: File) {
      const form = new FormData();
      form.append("file", file);
      return (
        await request("/conversations/upload", { method: "POST", body: form })
      ).json() as Promise<Conversation>;
    },
    sendMessage(query: string, conversationId: string) {
      return request("/chat/", {
        method: "POST",
        body: JSON.stringify({ query, conversation_id: conversationId }),
      });
    },
  };
}

export async function authenticate(mode: "login" | "register", form: FormData) {
  const body =
    mode === "login"
      ? { email: form.get("email"), password: form.get("password") }
      : {
          name: form.get("name"),
          email: form.get("email"),
          password: form.get("password"),
        };
  const response = await fetch(
    `${API_URL}/auth/${mode === "login" ? "login" : "register"}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
  const data = await response.json().catch(() => null);
  if (!response.ok || !data?.access_token)
    throw new ApiError(data?.detail ?? "Could not sign in", response.status);
  return data.access_token as string;
}

export async function readAssistantStream(
  response: Response,
  onToken: (content: string) => void,
) {
  const reader = response.body?.getReader();
  if (!reader) throw new Error("Streaming is not supported by this browser");

  const decoder = new TextDecoder();
  let buffer = "";
  let done = false;
  while (!done) {
    const result = await reader.read();
    done = result.done;
    buffer += decoder.decode(result.value, { stream: !done });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const event = JSON.parse(line.slice(6));
      if (event.event === "token") onToken(event.content);
      if (event.event === "error") {
        throw new Error(event.content ?? "The assistant could not answer.");
      }
    }
  }
}
