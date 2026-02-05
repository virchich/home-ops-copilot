import type { Season } from '../types';

interface SeasonSelectorProps {
  selected: Season | null;
  onSelect: (season: Season) => void;
  disabled?: boolean;
}

const seasons: { value: Season; label: string; icon: string }[] = [
  { value: 'winter', label: 'Winter', icon: '❄️' },
  { value: 'spring', label: 'Spring', icon: '🌱' },
  { value: 'summer', label: 'Summer', icon: '☀️' },
  { value: 'fall', label: 'Fall', icon: '🍂' },
];

export function SeasonSelector({ selected, onSelect, disabled }: SeasonSelectorProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {seasons.map((season) => (
        <button
          key={season.value}
          onClick={() => onSelect(season.value)}
          disabled={disabled}
          className={`
            px-4 py-2 rounded-lg text-sm font-medium transition-colors
            disabled:opacity-50 disabled:cursor-not-allowed
            ${
              selected === season.value
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
            }
          `}
        >
          <span className="mr-1.5">{season.icon}</span>
          {season.label}
        </button>
      ))}
    </div>
  );
}
