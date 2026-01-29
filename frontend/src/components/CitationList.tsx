import { useState } from 'react';
import type { Citation } from '../types';
import { CitationItem } from './CitationItem';

interface CitationListProps {
  citations: Citation[];
}

export function CitationList({ citations }: CitationListProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (citations.length === 0) {
    return (
      <div className="text-sm text-gray-500 italic">
        No sources available
      </div>
    );
  }

  return (
    <div className="mt-3">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900 transition-colors"
      >
        <svg
          className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        <span className="font-medium">
          {citations.length} source{citations.length !== 1 ? 's' : ''}
        </span>
      </button>
      {isExpanded && (
        <div className="mt-2 space-y-2">
          {citations.map((citation, index) => (
            <CitationItem key={index} citation={citation} index={index} />
          ))}
        </div>
      )}
    </div>
  );
}
