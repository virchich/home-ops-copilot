import { useState, useRef, useEffect } from 'react';
import type { ChatMessage as ChatMessageType } from './types';
import { askQuestion } from './api/client';
import { ChatInput } from './components/ChatInput';
import { ChatMessage } from './components/ChatMessage';

function App() {
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (question: string) => {
    const messageId = Date.now().toString();

    // Add message with loading state
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

  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Header */}
      <header className="flex-shrink-0 border-b border-gray-200 bg-white px-4 py-3">
        <div className="max-w-3xl mx-auto">
          <h1 className="text-lg font-semibold text-gray-900">Home Ops Copilot</h1>
          <p className="text-sm text-gray-500">Ask questions about your home maintenance</p>
        </div>
      </header>

      {/* Messages area */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full py-12 text-center">
              <div className="text-gray-400 mb-4">
                <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
              </div>
              <h2 className="text-lg font-medium text-gray-900 mb-1">No messages yet</h2>
              <p className="text-sm text-gray-500 max-w-sm">
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

export default App;
