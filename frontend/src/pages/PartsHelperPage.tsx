import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import type { HouseProfile, PartsLookupResponse } from '../types';
import { getHouseProfile, lookupParts } from '../api/client';
import { ThemeToggle } from '../components/ThemeToggle';
import { PartsQueryForm } from '../components/PartsQueryForm';
import { PartsResultsDisplay } from '../components/PartsResultsDisplay';

type PageState = 'idle' | 'loading' | 'results';

export function PartsHelperPage() {
  const [profile, setProfile] = useState<HouseProfile | null>(null);
  const [isLoadingProfile, setIsLoadingProfile] = useState(true);
  const [pageState, setPageState] = useState<PageState>('idle');
  const [results, setResults] = useState<PartsLookupResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadProfile() {
      try {
        const p = await getHouseProfile();
        setProfile(p);
      } catch {
        setError('Failed to load house profile');
      } finally {
        setIsLoadingProfile(false);
      }
    }
    loadProfile();
  }, []);

  const handleLookup = async (query: string, deviceType?: string) => {
    setPageState('loading');
    setError(null);

    try {
      const response = await lookupParts({
        query,
        device_type: deviceType || null,
      });
      setResults(response);
      setPageState('results');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to look up parts');
      setPageState('idle');
    }
  };

  const handleNewQuery = () => {
    setPageState('idle');
    setResults(null);
    setError(null);
  };

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
                  Parts Helper
                </h1>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Find replacement parts and consumables
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {pageState === 'results' && (
                <button
                  onClick={handleNewQuery}
                  className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
                >
                  New Query
                </button>
              )}
              <ThemeToggle />
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-4xl mx-auto px-4 py-6">
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
            {/* Query form (shown in idle and loading states) */}
            {(pageState === 'idle' || pageState === 'loading') && (
              <PartsQueryForm
                profile={profile}
                onSubmit={handleLookup}
                isLoading={pageState === 'loading'}
              />
            )}

            {/* Results */}
            {pageState === 'results' && results && (
              <PartsResultsDisplay
                parts={results.parts}
                clarificationQuestions={results.clarification_questions}
                summary={results.summary}
                markdown={results.markdown}
                sourcesUsed={results.sources_used}
              />
            )}
          </div>
        )}
      </main>
    </div>
  );
}
