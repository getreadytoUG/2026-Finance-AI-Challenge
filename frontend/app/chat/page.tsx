"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { sendChatMessage } from "@/lib/api";

type ChatEntry = { role: "user" | "assistant"; content: string };

export default function ChatPage() {
  const [token, setToken] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [history, setHistory] = useState<ChatEntry[]>([]);
  const router = useRouter();

  useEffect(() => {
    const stored = localStorage.getItem("token");
    if (!stored) {
      router.push("/login");
      return;
    }
    setToken(stored);
  }, [router]);

  async function handleSend() {
    if (!token || !input.trim()) return;
    const userMessage = input;
    setHistory((h) => [...h, { role: "user", content: userMessage }]);
    setInput("");
    try {
      const reply = await sendChatMessage(token, userMessage);
      setHistory((h) => [...h, { role: "assistant", content: reply }]);
    } catch {
      setHistory((h) => [...h, { role: "assistant", content: "(오류가 발생했습니다)" }]);
    }
  }

  return (
    <main style={{ maxWidth: 600, margin: "40px auto" }}>
      <h1>AI 금융 비서</h1>
      <div style={{ minHeight: 300, border: "1px solid #ccc", padding: 12, marginBottom: 12 }}>
        {history.map((entry, i) => (
          <p key={i}>
            <strong>{entry.role === "user" ? "나" : "AI"}:</strong> {entry.content}
          </p>
        ))}
      </div>
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleSend()}
        style={{ width: "80%" }}
      />
      <button onClick={handleSend}>전송</button>
    </main>
  );
}
