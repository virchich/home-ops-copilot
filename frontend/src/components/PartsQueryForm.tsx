import { useState, useMemo } from 'react';
import type { HouseProfile } from '../types';

interface PartsQueryFormProps {
  profile: HouseProfile;
  onSubmit: (query: string, deviceType?: string) => void;
  isLoading: boolean;
}

const quickQueries = [
  { label: 'All filters', query: 'What filters do I need for all my systems?' },
  { label: 'All consumables', query: 'What consumables and replacement parts should I stock up on?' },
];

export function PartsQueryForm({ profile, onSubmit, isLoading }: PartsQueryFormProps) {
  const [query, setQuery] = useState('');
  const [selectedDevice, setSelectedDevice] = useState<string | undefined>(undefined);

  const installedDevices = useMemo(
    () => Object.keys(profile.systems).map((key) => ({
      key,
      label: key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
    })),
    [profile.systems]
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    onSubmit(query.trim(), selectedDevice);
  };

  const handleQuickQuery = (q: string) => {
    setQuery(q);
    setSelectedDevice(undefined);
    onSubmit(q, undefined);
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="space-y-4">
        {/* Query input */}
        <div>
          <label
            htmlFor="parts-query"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            What parts or consumables do you need?
          </label>
          <textarea
            id="parts-query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g., What filter does my furnace need? What size humidifier pad do I buy?"
            className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
            rows={3}
            disabled={isLoading}
          />
        </div>

        {/* Quick query chips */}
        <div className="flex flex-wrap gap-2">
          <span className="text-xs text-gray-500 dark:text-gray-400 self-center">Quick:</span>
          {quickQueries.map((qq) => (
            <button
              key={qq.label}
              type="button"
              onClick={() => handleQuickQuery(qq.query)}
              disabled={isLoading}
              className="px-3 py-1 text-xs font-medium rounded-full border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white transition-colors disabled:opacity-50"
            >
              {qq.label}
            </button>
          ))}
        </div>

        {/* Device filter buttons */}
        <div>
          <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
            Filter by device (optional)
          </label>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setSelectedDevice(undefined)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors ${
                selectedDevice === undefined
                  ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 border-blue-300 dark:border-blue-700'
                  : 'border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              All
            </button>
            {installedDevices.map(({ key, label }) => (
              <button
                key={key}
                type="button"
                onClick={() => setSelectedDevice(selectedDevice === key ? undefined : key)}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors ${
                  selectedDevice === key
                    ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 border-blue-300 dark:border-blue-700'
                    : 'border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={isLoading || !query.trim()}
          className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {isLoading ? (
            <>
              <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Looking up parts...
            </>
          ) : (
            'Look Up Parts'
          )}
        </button>
      </div>
    </form>
  );
}
