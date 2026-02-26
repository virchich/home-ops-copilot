import { useState } from 'react';
import type { PartRecommendation, ClarificationQuestion } from '../types';
import { ConfidenceBadge } from './ConfidenceBadge';
import { copyToClipboard, downloadMarkdown } from '../utils/export';

interface PartsResultsDisplayProps {
  parts: PartRecommendation[];
  clarificationQuestions: ClarificationQuestion[];
  summary: string;
  markdown: string;
  sourcesUsed: string[];
}

export function PartsResultsDisplay({
  parts,
  clarificationQuestions,
  summary,
  markdown,
  sourcesUsed,
}: PartsResultsDisplayProps) {
  const [copied, setCopied] = useState(false);

  // Group parts by device_type
  const grouped: Record<string, PartRecommendation[]> = {};
  for (const part of parts) {
    if (!grouped[part.device_type]) {
      grouped[part.device_type] = [];
    }
    grouped[part.device_type].push(part);
  }

  const handleCopy = async () => {
    const ok = await copyToClipboard(markdown);
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleExport = () => {
    downloadMarkdown(markdown, 'parts-list.md');
  };

  return (
    <div className="space-y-6">
      {/* Summary */}
      {summary && (
        <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <p className="text-sm text-blue-800 dark:text-blue-300">{summary}</p>
        </div>
      )}

      {/* Parts by device */}
      {Object.entries(grouped).map(([deviceType, deviceParts]) => {
        const deviceLabel = deviceType.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
        return (
          <div key={deviceType}>
            <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-3">
              {deviceLabel}
            </h3>
            <div className="grid gap-3 sm:grid-cols-2">
              {deviceParts.map((part, idx) => (
                <PartCard key={`${deviceType}-${idx}`} part={part} />
              ))}
            </div>
          </div>
        );
      })}

      {/* No parts found */}
      {parts.length === 0 && (
        <div className="p-6 text-center text-sm text-gray-500 dark:text-gray-400">
          No parts identified from available documentation.
        </div>
      )}

      {/* Clarification questions */}
      {clarificationQuestions.length > 0 && (
        <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
          <h3 className="text-sm font-semibold text-yellow-800 dark:text-yellow-300 mb-2">
            Missing Information
          </h3>
          <p className="text-xs text-yellow-700 dark:text-yellow-400 mb-3">
            The following details would help identify parts more precisely. Try re-querying with this information:
          </p>
          <ul className="space-y-2">
            {clarificationQuestions.map((q) => (
              <li key={q.id} className="text-sm">
                <span className="font-medium text-yellow-800 dark:text-yellow-300">{q.question}</span>
                <span className="block text-xs text-yellow-600 dark:text-yellow-500 mt-0.5">
                  {q.reason}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Sources */}
      {sourcesUsed.length > 0 && (
        <div className="text-xs text-gray-500 dark:text-gray-400">
          Sources: {sourcesUsed.join(', ')}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={handleCopy}
          className="px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-400 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        >
          {copied ? 'Copied!' : 'Copy Markdown'}
        </button>
        <button
          onClick={handleExport}
          className="px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-400 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        >
          Export
        </button>
      </div>
    </div>
  );
}

function PartCard({ part }: { part: PartRecommendation }) {
  return (
    <div className="p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
      <div className="flex items-start justify-between gap-2 mb-2">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white">{part.part_name}</h4>
        <ConfidenceBadge level={part.confidence} />
      </div>

      <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">{part.description}</p>

      <div className="space-y-1">
        {part.part_number && (
          <div className="text-xs">
            <span className="font-medium text-gray-700 dark:text-gray-300">Part/Size: </span>
            <span className="text-gray-900 dark:text-white font-mono">{part.part_number}</span>
          </div>
        )}
        {part.device_model && (
          <div className="text-xs">
            <span className="font-medium text-gray-700 dark:text-gray-300">For model: </span>
            <span className="text-gray-600 dark:text-gray-400">{part.device_model}</span>
          </div>
        )}
        {part.replacement_interval && (
          <div className="text-xs">
            <span className="font-medium text-gray-700 dark:text-gray-300">Replace: </span>
            <span className="text-gray-600 dark:text-gray-400">{part.replacement_interval}</span>
          </div>
        )}
        {part.where_to_buy && (
          <div className="text-xs">
            <span className="font-medium text-gray-700 dark:text-gray-300">Where to buy: </span>
            <span className="text-gray-600 dark:text-gray-400">{part.where_to_buy}</span>
          </div>
        )}
        {part.source_doc && (
          <div className="text-xs text-gray-500 dark:text-gray-500 italic mt-1">
            Source: {part.source_doc}
          </div>
        )}
        {part.notes && (
          <div className="mt-2 text-xs p-2 bg-gray-50 dark:bg-gray-700/50 rounded text-gray-600 dark:text-gray-400">
            {part.notes}
          </div>
        )}
      </div>
    </div>
  );
}
