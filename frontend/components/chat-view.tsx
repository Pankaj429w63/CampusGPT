import React, { useRef, useEffect } from 'react';
import {
  BotIcon,
  UserIcon,
  SendIcon,
  InfoIcon,
} from './icons';

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  isDemo?: boolean;
}

interface ChatViewProps {
  messages: ChatMessage[];
  inputQuery: string;
  setInputQuery: (val: string) => void;
  isLoading: boolean;
  onSendMessage: () => void;
}

export function ChatView({
  messages,
  inputQuery,
  setInputQuery,
  isLoading,
  onSendMessage,
}: ChatViewProps) {
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="flex flex-col h-[calc(100vh-8.5rem)] rounded-2xl border border-slate-200/90 bg-white shadow-xs overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50/50 px-6 py-3.5">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white shadow-xs">
            <BotIcon className="h-4 w-4" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-slate-900">CampusGPT Assistant</h2>
            <div className="flex items-center gap-1.5 text-[11px] text-emerald-600 font-medium">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              <span>Ready for questions</span>
            </div>
          </div>
        </div>
        <div className="rounded-full bg-blue-50 px-2.5 py-0.5 text-[11px] font-medium text-blue-700 border border-blue-100">
          Demo Mode
        </div>
      </div>

      {/* Messages list */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-3 max-w-2xl ${
              msg.sender === 'user' ? 'ml-auto flex-row-reverse' : 'mr-auto'
            }`}
          >
            <div
              className={`flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-lg text-xs font-semibold ${
                msg.sender === 'user' ? 'bg-slate-800 text-white' : 'bg-blue-600 text-white'
              }`}
            >
              {msg.sender === 'user' ? <UserIcon className="h-4 w-4" /> : <BotIcon className="h-4 w-4" />}
            </div>

            <div className="space-y-1">
              <div
                className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  msg.sender === 'user'
                    ? 'bg-blue-600 text-white font-medium rounded-tr-none'
                    : 'bg-slate-100 text-slate-800 border border-slate-200/80 rounded-tl-none whitespace-pre-line'
                }`}
              >
                {msg.text}
              </div>

              {msg.isDemo && (
                <div className="flex items-center gap-1 text-[11px] text-amber-600 px-1 font-medium">
                  <InfoIcon className="h-3 w-3" />
                  <span>Demonstration response (AI backend integration coming next)</span>
                </div>
              )}
              <span className="block text-[10px] text-slate-400 px-1">
                {msg.timestamp}
              </span>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-3 max-w-2xl mr-auto">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-white">
              <BotIcon className="h-4 w-4 animate-spin" />
            </div>
            <div className="rounded-2xl rounded-tl-none bg-slate-100 border border-slate-200/80 px-4 py-3 text-sm text-slate-500 flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-blue-500 animate-bounce" />
              <span className="h-2 w-2 rounded-full bg-blue-500 animate-bounce [animation-delay:0.2s]" />
              <span className="h-2 w-2 rounded-full bg-blue-500 animate-bounce [animation-delay:0.4s]" />
              <span className="text-xs text-slate-400 ml-1">CampusGPT is thinking...</span>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Input section */}
      <div className="border-t border-slate-200 p-4 bg-slate-50/50">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            onSendMessage();
          }}
          className="flex gap-2"
        >
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            placeholder="Type your question for CampusGPT..."
            className="flex-1 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 focus:border-blue-500 focus:outline-hidden focus:ring-4 focus:ring-blue-500/10"
          />
          <button
            type="submit"
            disabled={!inputQuery.trim() || isLoading}
            className="flex items-center gap-1.5 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-xs hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors cursor-pointer"
          >
            <span>Send</span>
            <SendIcon className="h-4 w-4" />
          </button>
        </form>
      </div>
    </div>
  );
}

