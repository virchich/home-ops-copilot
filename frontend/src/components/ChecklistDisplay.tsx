import { useState } from 'react';
import Markdown from 'react-markdown';
import type { Season } from '../types';

interface ChecklistDisplayProps {
  markdown: string;
  season: Season;
  houseName: string;
  sourcesUsed: string[];
}

export function ChecklistDisplay({ markdown, season, houseName, sourcesUsed }: ChecklistDisplayProps) {
  const [copied, setCopied] = useState(false);

  const handleExport = () => {
    const blob = new Blob([markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${season}-maintenance-plan.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header with actions */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">
            {season.charAt(0).toUpperCase() + season.slice(1)} Maintenance Plan
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {houseName}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleCopy}
            className="px-3 py-1.5 text-sm font-medium rounded-md bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
          >
            {copied ? (
              <>
                <span className="mr-1.5">✓</span>
                Copied
              </>
            ) : (
              <>
                <span className="mr-1.5">📋</span>
                Copy
              </>
            )}
          </button>
          <button
            onClick={handleExport}
            className="px-3 py-1.5 text-sm font-medium rounded-md bg-blue-600 text-white hover:bg-blue-700 transition-colors"
          >
            <span className="mr-1.5">⬇️</span>
            Export
          </button>
        </div>
      </div>

      {/* Markdown content */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 sm:p-6">
        <div className="prose prose-sm prose-gray dark:prose-invert max-w-none checklist-content">
          <Markdown
            components={{
              // Style checkboxes nicely
              input: ({ ...props }) => (
                <input
                  {...props}
                  className="mr-2 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 align-middle"
                />
              ),
              // Render nested lists properly - notes appear as sub-items
              ul: ({ children, ...props }) => (
                <ul className="list-none pl-0 space-y-3" {...props}>
                  {children}
                </ul>
              ),
              li: ({ children, ...props }) => (
                <li className="pl-0" {...props}>
                  {children}
                </li>
              ),
              // Make task text more readable
              strong: ({ children, ...props }) => (
                <strong className="font-semibold text-gray-900 dark:text-white" {...props}>
                  {children}
                </strong>
              ),
              // Style device type italics
              em: ({ children, ...props }) => (
                <em className="text-blue-600 dark:text-blue-400 not-italic font-medium text-sm" {...props}>
                  {children}
                </em>
              ),
            }}
          >
            {markdown}
          </Markdown>
        </div>
      </div>

      {/* Sources used */}
      {sourcesUsed.length > 0 && (
        <div className="text-xs text-gray-500 dark:text-gray-400">
          <span className="font-medium">Sources: </span>
          {sourcesUsed.join(', ')}
        </div>
      )}
    </div>
  );
}
