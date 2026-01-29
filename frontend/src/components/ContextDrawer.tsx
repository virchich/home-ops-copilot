import { useState } from 'react';

interface ContextDrawerProps {
  contexts: string[];
}

export function ContextDrawer({ contexts }: ContextDrawerProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (contexts.length === 0) {
    return null;
  }

  return (
    <div className="mt-3 border-t border-gray-100 pt-3">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 transition-colors"
      >
        <svg
          className={`w-3 h-3 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        <span>Debug: Retrieved chunks ({contexts.length})</span>
      </button>
      {isExpanded && (
        <div className="mt-2 space-y-2 max-h-64 overflow-y-auto">
          {contexts.map((context, index) => (
            <div
              key={index}
              className="text-xs text-gray-500 bg-gray-50 p-2 rounded font-mono whitespace-pre-wrap"
            >
              {context}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
