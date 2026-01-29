import type { RiskLevel } from '../types';

interface RiskBadgeProps {
  level: RiskLevel;
}

const badgeStyles: Record<RiskLevel, string> = {
  LOW: 'bg-green-100 text-green-800 border-green-200',
  MED: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  HIGH: 'bg-red-100 text-red-800 border-red-200',
};

const labels: Record<RiskLevel, string> = {
  LOW: 'Low Risk',
  MED: 'Medium Risk',
  HIGH: 'High Risk',
};

export function RiskBadge({ level }: RiskBadgeProps) {
  return (
    <div className="flex items-center gap-2">
      <span
        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${badgeStyles[level]}`}
      >
        {labels[level]}
      </span>
      {level === 'HIGH' && (
        <span className="text-xs text-red-600 font-medium">
          Consider calling a licensed professional
        </span>
      )}
    </div>
  );
}
