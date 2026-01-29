import { useState, useRef, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import type { ChatMessage as ChatMessageType } from '../types';
import { askQuestion } from '../api/client';
import { ChatInput } from '../components/ChatInput';
import { ChatMessage } from '../components/ChatMessage';
import { ThemeToggle } from '../components/ThemeToggle';

const STORAGE_KEY = 'home-ops-copilot-chat-history';

export function ChatPage() {
  const [messages, setMessages] = useState<ChatMessageType[]>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        return parsed.filter((msg: ChatMessageType) => !msg.isLoading);
      } catch {
        return [];
      }
    }
    return [];
  });

  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Save to localStorage whenever messages change
  useEffect(() => {
    const completedMessages = messages.filter((msg) => !msg.isLoading);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(completedMessages));
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (question: string) => {
    const messageId = Date.now().toString();

    const newMessage: ChatMessageType = {
      id: messageId,
      question,
      response: null,
      isLoading: true,
      error: null,
    };

    setMessages((prev) => [...prev, newMessage]);
    setIsLoading(true);

    try {
      const response = await askQuestion(question);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === messageId
            ? { ...msg, response, isLoading: false }
            : msg
        )
      );
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred';
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === messageId
            ? { ...msg, error: errorMessage, isLoading: false }
            : msg
        )
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearChat = useCallback(() => {
    setMessages([]);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  const handleExportMarkdown = useCallback(() => {
    if (messages.length === 0) return;

    const markdown = messages
      .filter((msg) => msg.response)
      .map((msg) => {
        const lines: string[] = [];
        lines.push(`## Q: ${msg.question}`);
        lines.push('');
        if (msg.response) {
          lines.push(msg.response.answer);
          lines.push('');
          lines.push(`**Risk Level:** ${msg.response.risk_level}`);
          if (msg.response.citations.length > 0) {
            lines.push('');
            lines.push('### Sources');
            msg.response.citations.forEach((citation, i) => {
              let source = `${i + 1}. ${citation.source}`;
              if (citation.page) source += ` (p. ${citation.page})`;
              if (citation.section) source += ` - ${citation.section}`;
              lines.push(source);
            });
          }
        } else if (msg.error) {
          lines.push(`*Error: ${msg.error}*`);
        }
        lines.push('');
        lines.push('---');
        lines.push('');
        return lines.join('\n');
      })
      .join('\n');

    const header = `# Home Ops Copilot - Chat Export\n\n*Exported: ${new Date().toLocaleString()}*\n\n---\n\n`;
    const fullMarkdown = header + markdown;

    const blob = new Blob([fullMarkdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `home-ops-chat-${new Date().toISOString().split('T')[0]}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [messages]);

  return (
    <div className="flex flex-col h-screen bg-white dark:bg-gray-900 transition-colors">
      {/* Header */}
      <header className="flex-shrink-0 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 sm:px-4 py-3">
        <div className="max-w-3xl mx-auto flex items-center justify-between gap-2">
          <div className="flex items-center gap-3 min-w-0">
            {/* Back button */}
            <Link
              to="/"
              className="p-2 -ml-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
              title="Back to home"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </Link>
            <div>
              <h1 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white truncate">Ask a Question</h1>
              <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 hidden sm:block">Get answers about your home systems</p>
            </div>
          </div>
          <div className="flex items-center gap-1 sm:gap-2 flex-shrink-0">
            <ThemeToggle />

            {messages.length > 0 && (
              <>
                <button
                  onClick={handleExportMarkdown}
                  className="inline-flex items-center gap-1 px-2 sm:px-3 py-1.5 text-sm text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
                  title="Export as Markdown"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  <span className="hidden sm:inline">Export</span>
                </button>
                <button
                  onClick={handleClearChat}
                  className="inline-flex items-center gap-1 px-2 sm:px-3 py-1.5 text-sm text-gray-600 dark:text-gray-300 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md transition-colors"
                  title="Clear chat history"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                  <span className="hidden sm:inline">Clear</span>
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Messages area */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-3 sm:px-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full py-12 text-center">
              <div className="text-gray-400 dark:text-gray-500 mb-4">
                <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
              </div>
              <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-1">No messages yet</h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 max-w-sm px-4">
                Ask a question about your furnace, HRV, water heater, or other home systems.
              </p>
            </div>
          ) : (
            <div className="py-4">
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </main>

      {/* Input area */}
      <div className="flex-shrink-0 max-w-3xl mx-auto w-full">
        <ChatInput onSubmit={handleSubmit} disabled={isLoading} />
      </div>
    </div>
  );
}
