import { useState } from 'react';
import type { Season, ChecklistItem } from '../types';
import { copyToClipboard, downloadMarkdown } from '../utils/export';

interface ChecklistDisplayProps {
  checklistItems: ChecklistItem[];
  markdown: string;
  season: Season;
  houseName: string;
  sourcesUsed: string[];
  onDownloadCalendar?: () => void;
  isDownloadingCalendar?: boolean;
}

const priorityConfig = {
  high: {
    label: 'High Priority',
    borderColor: 'border-l-red-500',
    badgeColor: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  },
  medium: {
    label: 'Medium Priority',
    borderColor: 'border-l-yellow-500',
    badgeColor: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  },
  low: {
    label: 'Low Priority',
    borderColor: 'border-l-green-500',
    badgeColor: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  },
};

function TaskCard({ item }: { item: ChecklistItem }) {
  const config = priorityConfig[item.priority as keyof typeof priorityConfig] || priorityConfig.medium;

  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 border-l-4 ${config.borderColor} p-4 hover:shadow-md transition-shadow`}
    >
      {/* Header: Title */}
      <h4 className="font-semibold text-gray-900 dark:text-white text-base leading-snug mb-2">
        {item.task}
      </h4>

      {/* Meta: Device type, frequency, priority */}
      <div className="flex flex-wrap gap-2 mb-3">
        {item.device_type && (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
            {item.device_type}
          </span>
        )}
        {item.frequency && (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300">
            {item.frequency}
          </span>
        )}
        {item.estimated_time && (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400">
            {item.estimated_time}
          </span>
        )}
      </div>

      {/* Notes/Description */}
      {item.notes && (
        <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
          {item.notes}
        </p>
      )}

      {/* Source */}
      {item.source_doc && (
        <p className="mt-2 text-xs text-gray-400 dark:text-gray-500">
          Source: {item.source_doc}
        </p>
      )}
    </div>
  );
}

export function ChecklistDisplay({ checklistItems, markdown, season, houseName, sourcesUsed, onDownloadCalendar, isDownloadingCalendar }: ChecklistDisplayProps) {
  const [copied, setCopied] = useState(false);

  const handleExport = () => {
    downloadMarkdown(markdown, `${season}-maintenance-plan.md`);
  };

  const handleCopy = async () => {
    const ok = await copyToClipboard(markdown);
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // Group items by priority
  const highPriority = checklistItems.filter((item) => item.priority === 'high');
  const mediumPriority = checklistItems.filter((item) => item.priority === 'medium');
  const lowPriority = checklistItems.filter((item) => item.priority === 'low');

  return (
    <div className="space-y-6">
      {/* Header with actions */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-gray-200 dark:border-gray-700">
        <div>
          <h3 className="text-xl font-bold text-gray-900 dark:text-white">
            {season.charAt(0).toUpperCase() + season.slice(1)} Maintenance Plan
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {houseName} • {checklistItems.length} tasks
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleCopy}
            className="inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-md bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
          >
            {copied ? (
              <>
                <svg className="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Copied
              </>
            ) : (
              <>
                <svg className="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                Copy
              </>
            )}
          </button>
          <button
            onClick={handleExport}
            className="inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-md bg-blue-600 text-white hover:bg-blue-700 transition-colors"
          >
            <svg className="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Export
          </button>
          {onDownloadCalendar && (
            <button
              onClick={onDownloadCalendar}
              disabled={isDownloadingCalendar}
              className="inline-flex items-center px-3 py-1.5 text-sm font-medium rounded-md bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title="Download calendar reminders (.ics)"
            >
              <svg className="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              {isDownloadingCalendar ? 'Generating...' : 'Calendar'}
            </button>
          )}
        </div>
      </div>

      {/* High Priority Section */}
      {highPriority.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <h4 className="text-lg font-semibold text-gray-900 dark:text-white">High Priority</h4>
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
              {highPriority.length}
            </span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {highPriority.map((item, index) => (
              <TaskCard key={`high-${index}`} item={item} />
            ))}
          </div>
        </div>
      )}

      {/* Medium Priority Section */}
      {mediumPriority.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <h4 className="text-lg font-semibold text-gray-900 dark:text-white">Medium Priority</h4>
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400">
              {mediumPriority.length}
            </span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {mediumPriority.map((item, index) => (
              <TaskCard key={`medium-${index}`} item={item} />
            ))}
          </div>
        </div>
      )}

      {/* Low Priority Section */}
      {lowPriority.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <h4 className="text-lg font-semibold text-gray-900 dark:text-white">Low Priority</h4>
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
              {lowPriority.length}
            </span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {lowPriority.map((item, index) => (
              <TaskCard key={`low-${index}`} item={item} />
            ))}
          </div>
        </div>
      )}

      {/* Sources */}
      {sourcesUsed.length > 0 && (
        <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            <span className="font-medium">Sources referenced: </span>
            {sourcesUsed.join(', ')}
          </p>
        </div>
      )}
    </div>
  );
}
