"use client";

import { useState, useEffect, useCallback } from "react";
import { ChatMessage, ChatAction } from "../types";

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch("/api/chat/history");
        if (res.ok) {
          const data = await res.json();
          setMessages(
            Array.isArray(data) ? data : data.messages || []
          );
        }
      } catch {
        // ignore
      } finally {
        setInitialLoading(false);
      }
    })();
  }, []);

  const sendMessage = useCallback(
    async (content: string): Promise<ChatMessage | null> => {
      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setLoading(true);

      try {
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: content }),
        });
        if (res.ok) {
          const data = await res.json();
          const actions: ChatAction[] = [];

          if (data.actions) {
            actions.push(...data.actions);
          }
          if (data.trades) {
            for (const t of data.trades) {
              actions.push({
                type: "trade",
                success: true,
                message: `${t.side.toUpperCase()} ${t.quantity} ${t.ticker}`,
              });
            }
          }
          if (data.watchlist_changes) {
            for (const w of data.watchlist_changes) {
              actions.push({
                type: "watchlist",
                success: true,
                message: `${w.action.toUpperCase()} ${w.ticker}`,
              });
            }
          }

          const assistantMsg: ChatMessage = {
            id: crypto.randomUUID(),
            role: "assistant",
            content: data.message || data.content || "",
            created_at: new Date().toISOString(),
            actions: actions.length > 0 ? actions : undefined,
          };
          setMessages((prev) => [...prev, assistantMsg]);
          return assistantMsg;
        }
      } catch {
        const errMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: "Failed to get a response. Please try again.",
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, errMsg]);
      } finally {
        setLoading(false);
      }
      return null;
    },
    []
  );

  return { messages, loading, initialLoading, sendMessage };
}
