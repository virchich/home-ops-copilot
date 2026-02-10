import { useState, useEffect } from 'react';
import type { HouseProfile, TroubleshootStartRequest } from '../types';

interface IntakeFormProps {
  profile: HouseProfile;
  onSubmit: (request: TroubleshootStartRequest) => void;
  isLoading: boolean;
}

const URGENCY_OPTIONS = [
  { value: 'low', label: 'Low', description: 'No rush, just want to investigate' },
  { value: 'medium', label: 'Medium', description: 'Would like to resolve soon' },
  { value: 'high', label: 'High', description: 'System not working, need it fixed' },
  { value: 'emergency', label: 'Emergency', description: 'Safety concern or urgent failure' },
];

export function IntakeForm({ profile, onSubmit, isLoading }: IntakeFormProps) {
  const [deviceType, setDeviceType] = useState('');
  const [symptom, setSymptom] = useState('');
  const [urgency, setUrgency] = useState('medium');
  const [additionalContext, setAdditionalContext] = useState('');

  // Get installed device types from house profile
  const installedDevices = Object.keys(profile.systems);

  // Set default device if only one
  useEffect(() => {
    if (installedDevices.length === 1) {
      setDeviceType(installedDevices[0]);
    }
  }, [installedDevices.length]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!deviceType || !symptom.trim()) return;

    onSubmit({
      device_type: deviceType,
      symptom: symptom.trim(),
      urgency,
      additional_context: additionalContext.trim() || null,
    });
  };

  const formatDeviceName = (name: string) =>
    name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Device selector */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Which device has the issue?
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {installedDevices.map((device) => (
            <button
              key={device}
              type="button"
              onClick={() => setDeviceType(device)}
              className={`px-3 py-2 text-sm rounded-lg border transition-colors ${
                deviceType === device
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-medium'
                  : 'border-gray-200 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:border-gray-300 dark:hover:border-gray-500'
              }`}
            >
              {formatDeviceName(device)}
            </button>
          ))}
        </div>
      </div>

      {/* Symptom textarea */}
      <div>
        <label
          htmlFor="symptom"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
        >
          What's the problem?
        </label>
        <textarea
          id="symptom"
          value={symptom}
          onChange={(e) => setSymptom(e.target.value)}
          placeholder="Describe the issue... (e.g., 'Furnace is running but no heat coming from vents')"
          rows={3}
          className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
        />
      </div>

      {/* Urgency radio */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          How urgent is this?
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {URGENCY_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setUrgency(opt.value)}
              className={`px-3 py-2 text-sm rounded-lg border transition-colors text-left ${
                urgency === opt.value
                  ? opt.value === 'emergency'
                    ? 'border-red-500 bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300 font-medium'
                    : 'border-blue-500 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-medium'
                  : 'border-gray-200 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:border-gray-300 dark:hover:border-gray-500'
              }`}
            >
              <div className="font-medium">{opt.label}</div>
              <div className="text-xs opacity-75">{opt.description}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Additional context */}
      <div>
        <label
          htmlFor="context"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
        >
          Additional context <span className="text-gray-400 font-normal">(optional)</span>
        </label>
        <textarea
          id="context"
          value={additionalContext}
          onChange={(e) => setAdditionalContext(e.target.value)}
          placeholder="When did it start? Anything changed recently? (e.g., 'Started after the power went out yesterday')"
          rows={2}
          className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
        />
      </div>

      {/* Submit */}
      <button
        type="submit"
        disabled={!deviceType || !symptom.trim() || isLoading}
        className="w-full px-4 py-2.5 text-sm font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isLoading ? (
          <span className="flex items-center justify-center gap-2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            Analyzing...
          </span>
        ) : (
          'Start Troubleshooting'
        )}
      </button>
    </form>
  );
}
