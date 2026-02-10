interface SafetyWarningProps {
  safetyMessage: string;
  recommendedProfessional: string | null;
}

export function SafetyWarning({ safetyMessage, recommendedProfessional }: SafetyWarningProps) {
  return (
    <div className="p-5 bg-red-50 dark:bg-red-900/20 border-2 border-red-300 dark:border-red-700 rounded-xl">
      {/* Warning icon + title */}
      <div className="flex items-center gap-2 mb-3">
        <svg
          className="w-6 h-6 text-red-600 dark:text-red-400 flex-shrink-0"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"
          />
        </svg>
        <h3 className="text-lg font-bold text-red-800 dark:text-red-300">
          Safety Stop
        </h3>
      </div>

      {/* Safety message */}
      <p className="text-sm text-red-700 dark:text-red-300 mb-4 leading-relaxed">
        {safetyMessage}
      </p>

      {/* Professional recommendation */}
      {recommendedProfessional && (
        <div className="p-3 bg-white dark:bg-gray-800 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-sm font-medium text-gray-900 dark:text-white mb-1">
            Recommended Professional
          </p>
          <p className="text-sm text-gray-700 dark:text-gray-300 capitalize">
            {recommendedProfessional}
          </p>
        </div>
      )}

      {/* Do not proceed warning */}
      <p className="mt-4 text-xs text-red-600 dark:text-red-400 font-medium">
        Do NOT attempt to troubleshoot this issue yourself. Follow the safety guidance above.
      </p>
    </div>
  );
}
