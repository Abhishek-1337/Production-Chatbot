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
  messages?: Message[];
};
