import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import type {
  HouseProfile,
  FollowupAnswer,
  TroubleshootStartRequest,
  TroubleshootStartResponse,
  TroubleshootDiagnoseResponse,
} from '../types';
import { getHouseProfile, startTroubleshooting, submitDiagnosis } from '../api/client';
import { IntakeForm } from '../components/IntakeForm';
import { FollowupQuestions } from '../components/FollowupQuestions';
import { DiagnosticStepsDisplay } from '../components/DiagnosticStepsDisplay';
import { SafetyWarning } from '../components/SafetyWarning';
import { ThemeToggle } from '../components/ThemeToggle';

type PagePhase = 'intake' | 'followup' | 'safety_stop' | 'diagnosis';

export function TroubleshootPage() {
  const [profile, setProfile] = useState<HouseProfile | null>(null);
  const [isLoadingProfile, setIsLoadingProfile] = useState(true);
  const [isLoadingIntake, setIsLoadingIntake] = useState(false);
  const [isLoadingDiagnosis, setIsLoadingDiagnosis] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [phase, setPhase] = useState<PagePhase>('intake');
  const [intakeResponse, setIntakeResponse] = useState<TroubleshootStartResponse | null>(null);
  const [diagnosisResponse, setDiagnosisResponse] = useState<TroubleshootDiagnoseResponse | null>(null);

  // Load house profile on mount
  useEffect(() => {
    async function loadProfile() {
      try {
        const data = await getHouseProfile();
        setProfile(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load house profile');
      } finally {
        setIsLoadingProfile(false);
      }
    }
    loadProfile();
  }, []);

  const handleStartTroubleshooting = async (request: TroubleshootStartRequest) => {
    setIsLoadingIntake(true);
    setError(null);

    try {
      const response = await startTroubleshooting(request);
      setIntakeResponse(response);

      if (response.is_safety_stop) {
        setPhase('safety_stop');
      } else {
        setPhase('followup');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start troubleshooting');
    } finally {
      setIsLoadingIntake(false);
    }
  };

  const handleSubmitAnswers = async (answers: FollowupAnswer[]) => {
    if (!intakeResponse) return;

    setIsLoadingDiagnosis(true);
    setError(null);

    try {
      const response = await submitDiagnosis({
        session_id: intakeResponse.session_id,
        answers,
      });
      setDiagnosisResponse(response);
      setPhase('diagnosis');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate diagnosis');
    } finally {
      setIsLoadingDiagnosis(false);
    }
  };

  const handleStartOver = () => {
    setPhase('intake');
    setIntakeResponse(null);
    setDiagnosisResponse(null);
    setError(null);
  };

  // Stepper
  const steps = [
    { key: 'intake', label: 'Describe Issue' },
    { key: 'followup', label: 'Follow-up Questions' },
    { key: 'diagnosis', label: 'Diagnosis' },
  ];
  const phaseOrder = ['intake', 'followup', 'diagnosis'];
  const currentStepIdx = phase === 'safety_stop' ? 1 : phaseOrder.indexOf(phase);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors">
      {/* Header */}
      <header className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <div className="max-w-4xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Link
                to="/"
                className="p-2 -ml-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
                title="Back to home"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
              </Link>
              <div>
                <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Troubleshoot
                </h1>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Guided diagnostic with safety guardrails
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {phase !== 'intake' && (
                <button
                  onClick={handleStartOver}
                  className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
                >
                  Start Over
                </button>
              )}
              <ThemeToggle />
            </div>
          </div>
        </div>
      </header>

      {/* Stepper */}
      <div className="max-w-4xl mx-auto px-4 py-4">
        <div className="flex items-center gap-2">
          {steps.map((step, idx) => (
            <div key={step.key} className="flex items-center gap-2 flex-1">
              <div
                className={`flex items-center gap-2 ${
                  idx <= currentStepIdx
                    ? 'text-blue-600 dark:text-blue-400'
                    : 'text-gray-400 dark:text-gray-500'
                }`}
              >
                <span
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                    idx < currentStepIdx
                      ? 'bg-blue-600 text-white'
                      : idx === currentStepIdx
                      ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 border border-blue-300 dark:border-blue-700'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500'
                  }`}
                >
                  {idx < currentStepIdx ? (
                    <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                  ) : (
                    idx + 1
                  )}
                </span>
                <span className="text-xs font-medium hidden sm:block">{step.label}</span>
              </div>
              {idx < steps.length - 1 && (
                <div
                  className={`flex-1 h-px ${
                    idx < currentStepIdx
                      ? 'bg-blue-300 dark:bg-blue-700'
                      : 'bg-gray-200 dark:bg-gray-700'
                  }`}
                />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Main content */}
      <main className="max-w-4xl mx-auto px-4 pb-8">
        {/* Error */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          </div>
        )}

        {/* Loading profile */}
        {isLoadingProfile ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
            <span className="ml-2 text-sm text-gray-500 dark:text-gray-400">Loading profile...</span>
          </div>
        ) : !profile ? (
          <div className="p-6 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-center">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              No house profile found. Please create one from the{' '}
              <Link to="/maintenance-plan" className="text-blue-600 dark:text-blue-400 hover:underline">
                Maintenance Plan
              </Link>{' '}
              page first.
            </p>
          </div>
        ) : (
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 sm:p-6">
            {/* Phase 1: Intake Form */}
            {phase === 'intake' && (
              <IntakeForm
                profile={profile}
                onSubmit={handleStartTroubleshooting}
                isLoading={isLoadingIntake}
              />
            )}

            {/* Phase 2a: Follow-up Questions */}
            {phase === 'followup' && intakeResponse && (
              <FollowupQuestions
                questions={intakeResponse.followup_questions}
                preliminaryAssessment={intakeResponse.preliminary_assessment}
                onSubmit={handleSubmitAnswers}
                isLoading={isLoadingDiagnosis}
              />
            )}

            {/* Phase 2b: Safety Stop */}
            {phase === 'safety_stop' && intakeResponse && (
              <SafetyWarning
                safetyMessage={intakeResponse.safety_message || 'A safety concern was detected.'}
                recommendedProfessional={intakeResponse.recommended_professional}
              />
            )}

            {/* Phase 3: Diagnosis Results */}
            {phase === 'diagnosis' && diagnosisResponse && (
              <DiagnosticStepsDisplay
                diagnosisSummary={diagnosisResponse.diagnosis_summary}
                steps={diagnosisResponse.diagnostic_steps}
                overallRiskLevel={diagnosisResponse.overall_risk_level}
                whenToCallProfessional={diagnosisResponse.when_to_call_professional}
                markdown={diagnosisResponse.markdown}
                sourcesUsed={diagnosisResponse.sources_used}
              />
            )}
          </div>
        )}
      </main>
    </div>
  );
}
