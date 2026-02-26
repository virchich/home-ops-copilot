import { useState } from 'react';
import type { ChatMessage as ChatMessageType } from '../types';
import Markdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { RiskBadge } from './RiskBadge';
import { CitationList } from './CitationList';
import { ContextDrawer } from './ContextDrawer';
import { copyToClipboard, formatMessageAsMarkdown } from '../utils/export';

interface ChatMessageProps {
  message: ChatMessageType;
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1">
      <span className="text-sm text-gray-500 dark:text-gray-400">Thinking</span>
      <div className="flex gap-1">
        <span className="w-1.5 h-1.5 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce [animation-delay:-0.3s]" />
        <span className="w-1.5 h-1.5 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce [animation-delay:-0.15s]" />
        <span className="w-1.5 h-1.5 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce" />
      </div>
    </div>
  );
}

export function ChatMessage({ message }: ChatMessageProps) {
  const [copied, setCopied] = useState(false);
  const isDark = document.documentElement.classList.contains('dark');

  const handleCopy = async () => {
    if (!message.response) return;

    const markdown = formatMessageAsMarkdown(
      message.question,
      message.response.answer,
      message.response.risk_level,
      message.response.citations,
    );
    const ok = await copyToClipboard(markdown);
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="space-y-3 sm:space-y-4 py-3 sm:py-4 border-b border-gray-100 dark:border-gray-800 last:border-b-0">
      {/* User question */}
      <div className="flex justify-end">
        <div className="max-w-[90%] sm:max-w-[80%] bg-blue-600 text-white rounded-lg px-3 sm:px-4 py-2">
          <p className="text-sm">{message.question}</p>
        </div>
      </div>

      {/* Assistant response */}
      <div className="flex justify-start">
        <div className="max-w-[90%] sm:max-w-[80%] bg-gray-100 dark:bg-gray-800 rounded-lg px-3 sm:px-4 py-3 group relative">
          {message.isLoading ? (
            <TypingIndicator />
          ) : message.error ? (
            <div className="text-red-600 dark:text-red-400">
              <p className="text-sm font-medium">Error</p>
              <p className="text-sm">{message.error}</p>
            </div>
          ) : message.response ? (
            <div>
              {/* Copy button - appears on hover */}
              <button
                onClick={handleCopy}
                className="absolute top-2 right-2 p-1.5 rounded-md bg-white/80 dark:bg-gray-700/80 hover:bg-white dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 opacity-0 group-hover:opacity-100 transition-opacity shadow-sm"
                title={copied ? 'Copied!' : 'Copy answer'}
              >
                {copied ? (
                  <svg className="w-4 h-4 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                )}
              </button>

              <div className="prose prose-sm prose-gray dark:prose-invert max-w-none">
                <Markdown
                  components={{
                    code({ className, children, ...props }) {
                      const match = /language-(\w+)/.exec(className || '');
                      const codeString = String(children).replace(/\n$/, '');

                      if (match) {
                        return (
                          <SyntaxHighlighter
                            style={isDark ? oneDark : oneLight}
                            language={match[1]}
                            PreTag="div"
                            customStyle={{
                              margin: 0,
                              borderRadius: '0.375rem',
                              fontSize: '0.8125rem',
                            }}
                          >
                            {codeString}
                          </SyntaxHighlighter>
                        );
                      }

                      // Inline code
                      return (
                        <code className="bg-gray-200 dark:bg-gray-700 px-1.5 py-0.5 rounded text-sm" {...props}>
                          {children}
                        </code>
                      );
                    },
                  }}
                >
                  {message.response.answer}
                </Markdown>
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
