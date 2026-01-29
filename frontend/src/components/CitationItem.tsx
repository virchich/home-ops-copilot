import type { Citation } from '../types';

interface CitationItemProps {
  citation: Citation;
  index: number;
}

export function CitationItem({ citation, index }: CitationItemProps) {
  return (
    <div className="border-l-2 border-gray-300 dark:border-gray-600 pl-3 py-2">
      <div className="flex items-baseline gap-2 flex-wrap">
        <span className="text-xs font-medium text-gray-500 dark:text-gray-400">[{index + 1}]</span>
        <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{citation.source}</span>
      </div>
      <div className="mt-1 flex flex-wrap gap-2 text-xs text-gray-500 dark:text-gray-400">
        {citation.page && <span>Page {citation.page}</span>}
        {citation.section && (
          <>
            {citation.page && <span>•</span>}
            <span>{citation.section}</span>
          </>
        )}
      </div>
      {citation.quote && (
        <blockquote className="mt-2 text-sm text-gray-600 dark:text-gray-300 italic border-l-2 border-gray-200 dark:border-gray-600 pl-2">
          "{citation.quote}"
        </blockquote>
      )}
    </div>
  );
}
