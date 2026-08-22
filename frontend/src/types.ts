export type User = { name: string; email: string };

export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  status?: "failed";
};

export type Conversation = {
  id: string;
  title: string;
  document_id: string;
  document_name?: string | null;
  created_at: string;
  updated_at: string;
  messages?: Message[] | null;
  total_messages?: number | null;
};

export type PaginatedMessages = {
  messages: Message[];
  next_cursor: string | null;
  has_more: boolean;
  total: number | null;
};
