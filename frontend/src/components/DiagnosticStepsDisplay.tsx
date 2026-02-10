import type { DiagnosticStep, RiskLevel } from '../types';
import { RiskBadge } from './RiskBadge';

interface DiagnosticStepsDisplayProps {
  diagnosisSummary: string;
  steps: DiagnosticStep[];
  overallRiskLevel: RiskLevel;
  whenToCallProfessional: string;
  markdown: string;
  sourcesUsed: string[];
}

export function DiagnosticStepsDisplay({
  diagnosisSummary,
  steps,
  overallRiskLevel,
  whenToCallProfessional,
  markdown,
  sourcesUsed,
}: DiagnosticStepsDisplayProps) {
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(markdown);
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement('textarea');
      textarea.value = markdown;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
    }
  };

  const handleExport = () => {
    const blob = new Blob([markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'troubleshooting-diagnosis.md';
    a.click();
    URL.revokeObjectURL(url);
  };

  const stepRiskStyles: Record<RiskLevel, string> = {
    LOW: 'border-l-green-400',
    MED: 'border-l-yellow-400',
    HIGH: 'border-l-red-400',
  };

  return (
    <div className="space-y-5">
      {/* Summary */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">Diagnosis</h3>
          <RiskBadge level={overallRiskLevel} />
        </div>
        <p className="text-sm text-gray-700 dark:text-gray-300">{diagnosisSummary}</p>
      </div>

      {/* Diagnostic steps */}
      <div className="space-y-3">
        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 uppercase tracking-wide">
          Steps to Resolve
        </h4>
        {steps.map((step) => (
          <div
            key={step.step_number}
            className={`p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 border-l-4 ${stepRiskStyles[step.risk_level]} rounded-lg`}
          >
            <div className="flex items-start gap-3">
              <span className="flex-shrink-0 w-7 h-7 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full flex items-center justify-center text-sm font-semibold">
                {step.step_number}
              </span>
              <div className="flex-1 space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {step.instruction}
                  </p>
                  {step.requires_professional && (
                    <span className="flex-shrink-0 px-2 py-0.5 text-xs font-medium bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-full">
                      Professional
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">Expected: </span>
                    <span className="text-gray-700 dark:text-gray-300">{step.expected_outcome}</span>
                  </div>
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">If not resolved: </span>
                    <span className="text-gray-700 dark:text-gray-300">{step.if_not_resolved}</span>
                  </div>
                </div>

                {step.source_doc && (
                  <p className="text-xs text-gray-400 dark:text-gray-500 italic">
                    Source: {step.source_doc}
                  </p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* When to call professional */}
      <div className="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
        <p className="text-sm font-medium text-amber-800 dark:text-amber-300 mb-1">
          When to Call a Professional
        </p>
        <p className="text-sm text-amber-700 dark:text-amber-400">{whenToCallProfessional}</p>
      </div>

      {/* Sources */}
      {sourcesUsed.length > 0 && (
        <div className="text-xs text-gray-500 dark:text-gray-400">
          <span className="font-medium">Sources:</span> {sourcesUsed.join(', ')}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2 pt-2">
        <button
          onClick={handleCopy}
          className="px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
        >
          Copy Markdown
        </button>
        <button
          onClick={handleExport}
          className="px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
        >
          Export .md
        </button>
      </div>
    </div>
  );
}
