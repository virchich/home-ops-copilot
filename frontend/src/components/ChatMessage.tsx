import type { ChatMessage as ChatMessageType } from '../types';
import Markdown from 'react-markdown';
import { RiskBadge } from './RiskBadge';
import { CitationList } from './CitationList';
import { ContextDrawer } from './ContextDrawer';

interface ChatMessageProps {
  message: ChatMessageType;
}

export function ChatMessage({ message }: ChatMessageProps) {
  return (
    <div className="space-y-4 py-4 border-b border-gray-100 last:border-b-0">
      {/* User question */}
      <div className="flex justify-end">
        <div className="max-w-[80%] bg-blue-600 text-white rounded-lg px-4 py-2">
          <p className="text-sm">{message.question}</p>
        </div>
      </div>

      {/* Assistant response */}
      <div className="flex justify-start">
        <div className="max-w-[80%] bg-gray-100 rounded-lg px-4 py-3">
          {message.isLoading ? (
            <div className="flex items-center gap-2 text-gray-500">
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span className="text-sm">Thinking...</span>
            </div>
          ) : message.error ? (
            <div className="text-red-600">
              <p className="text-sm font-medium">Error</p>
              <p className="text-sm">{message.error}</p>
            </div>
          ) : message.response ? (
            <div>
              <div className="prose prose-sm prose-gray max-w-none">
                <Markdown>{message.response.answer}</Markdown>
              </div>
              <div className="mt-3">
                <RiskBadge level={message.response.risk_level} />
              </div>
              <CitationList citations={message.response.citations} />
              <ContextDrawer contexts={message.response.contexts} />
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
