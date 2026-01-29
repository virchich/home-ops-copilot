import type { RiskLevel } from '../types';

interface RiskBadgeProps {
  level: RiskLevel;
}

const badgeStyles: Record<RiskLevel, string> = {
  LOW: 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300 border-green-200 dark:border-green-800',
  MED: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300 border-yellow-200 dark:border-yellow-800',
  HIGH: 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300 border-red-200 dark:border-red-800',
};

const labels: Record<RiskLevel, string> = {
  LOW: 'Low Risk',
  MED: 'Medium Risk',
  HIGH: 'High Risk',
};

export function RiskBadge({ level }: RiskBadgeProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span
        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${badgeStyles[level]}`}
      >
        {labels[level]}
      </span>
      {level === 'HIGH' && (
        <span className="text-xs text-red-600 dark:text-red-400 font-medium">
          Consider calling a licensed professional
        </span>
      )}
    </div>
  );
}
