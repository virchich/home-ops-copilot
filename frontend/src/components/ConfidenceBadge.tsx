import type { ConfidenceLevel } from '../types';

interface ConfidenceBadgeProps {
  level: ConfidenceLevel;
}

const badgeStyles: Record<ConfidenceLevel, string> = {
  confirmed:
    'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 border-green-200 dark:border-green-800',
  likely:
    'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 border-yellow-200 dark:border-yellow-800',
  uncertain:
    'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-600',
};

const badgeLabels: Record<ConfidenceLevel, string> = {
  confirmed: 'Confirmed',
  likely: 'Likely',
  uncertain: 'Uncertain',
};

export function ConfidenceBadge({ level }: ConfidenceBadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full border ${badgeStyles[level]}`}
    >
      {badgeLabels[level]}
    </span>
  );
}
