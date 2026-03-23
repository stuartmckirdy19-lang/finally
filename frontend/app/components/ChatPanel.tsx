"use client";

import { useState, useRef, useEffect } from "react";
import { ChatMessage } from "../types";
import { Send, Loader2 } from "lucide-react";

interface ChatPanelProps {
  messages: ChatMessage[];
  loading: boolean;
  onSend: (message: string) => Promise<ChatMessage | null>;
  onTradeComplete: () => void;
}

export default function ChatPanel({
  messages,
  loading,
  onSend,
  onTradeComplete,
}: ChatPanelProps) {
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const msg = input.trim();
    if (!msg || loading) return;
    setInput("");
    const result = await onSend(msg);
    if (result?.actions && result.actions.some((a) => a.type === "trade")) {
      onTradeComplete();
    }
  };

  return (
    <div className="flex flex-col h-full bg-bg-primary">
      <div className="px-3 py-2 border-b border-border">
        <h2 className="text-xs font-semibold text-accent-yellow uppercase tracking-wider">
          FinAlly AI
        </h2>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-3 py-2 space-y-3">
        {messages.length === 0 && !loading && (
          <div className="text-text-muted text-xs text-center mt-8">
            Ask me about your portfolio, market analysis, or to execute trades.
          </div>
        )}
        {messages.map((msg) => (
          <div key={msg.id}>
            <div
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[90%] rounded-lg px-3 py-2 text-xs leading-relaxed ${
                  msg.role === "user"
                    ? "bg-purple-secondary/30 text-text-primary"
                    : "bg-bg-secondary text-text-primary"
                }`}
              >
                <div className="whitespace-pre-wrap">{msg.content}</div>
              </div>
            </div>
            {msg.actions && msg.actions.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1 ml-1">
                {msg.actions.map((action, i) => (
                  <span
                    key={i}
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium ${
                      action.success
                        ? action.type === "trade"
                          ? "bg-blue-primary/20 text-blue-primary"
                          : "bg-accent-yellow/20 text-accent-yellow"
                        : "bg-loss/20 text-loss"
                    }`}
                  >
                    {action.message}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-bg-secondary rounded-lg px-3 py-2">
              <Loader2 size={14} className="animate-spin text-text-muted" />
            </div>
          </div>
        )}
      </div>

      <form
        onSubmit={handleSubmit}
        className="px-3 py-2 border-t border-border flex gap-2"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask FinAlly..."
          disabled={loading}
          className="flex-1 bg-bg-secondary text-text-primary text-xs px-3 py-2 rounded border border-border focus:border-purple-secondary focus:outline-none placeholder:text-text-muted/50 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="bg-purple-secondary text-white p-2 rounded hover:opacity-80 disabled:opacity-30 transition-opacity"
        >
          <Send size={14} />
        </button>
      </form>
    </div>
  );
}
