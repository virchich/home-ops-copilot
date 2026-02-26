import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import type { HouseProfile, Season, MaintenancePlanResponse } from '../types';
import { getHouseProfile, updateHouseProfile, generateMaintenancePlan, downloadMaintenanceIcs } from '../api/client';
import { SeasonSelector } from '../components/SeasonSelector';
import { ChecklistDisplay } from '../components/ChecklistDisplay';
import { HouseProfileEditor } from '../components/HouseProfileEditor';
import { ThemeToggle } from '../components/ThemeToggle';

export function MaintenancePlanPage() {
  const [profile, setProfile] = useState<HouseProfile | null>(null);
  const [selectedSeason, setSelectedSeason] = useState<Season | null>(null);
  const [plan, setPlan] = useState<MaintenancePlanResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingProfile, setIsLoadingProfile] = useState(true);
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [isDownloadingCalendar, setIsDownloadingCalendar] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  const handleGeneratePlan = async () => {
    if (!selectedSeason) return;

    setIsLoading(true);
    setError(null);

    try {
      const result = await generateMaintenancePlan(selectedSeason);
      setPlan(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate plan');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveProfile = async (updatedProfile: HouseProfile) => {
    setIsSavingProfile(true);
    setError(null);

    try {
      const saved = await updateHouseProfile(updatedProfile);
      setProfile(saved);
      setIsEditing(false);
      // Clear existing plan since profile changed
      setPlan(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save profile');
    } finally {
      setIsSavingProfile(false);
    }
  };

  const handleDownloadCalendar = async () => {
    if (!selectedSeason) return;
    setIsDownloadingCalendar(true);
    setError(null);

    try {
      await downloadMaintenanceIcs(selectedSeason);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate calendar');
    } finally {
      setIsDownloadingCalendar(false);
    }
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
                  Maintenance Plan
                </h1>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Generate seasonal maintenance checklists
                </p>
              </div>
            </div>
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {/* Error message */}
        {error && (
          <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          </div>
        )}

        {/* House Profile Section */}
        <section className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 sm:p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium text-gray-900 dark:text-white">
              House Profile
            </h2>
            {!isEditing && profile && (
              <button
                onClick={() => setIsEditing(true)}
                className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300"
              >
                Edit
              </button>
            )}
          </div>

          {isLoadingProfile ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
              <span className="ml-2 text-sm text-gray-500 dark:text-gray-400">Loading profile...</span>
            </div>
          ) : isEditing && profile ? (
            <HouseProfileEditor
              profile={profile}
              onSave={handleSaveProfile}
              onCancel={() => setIsEditing(false)}
              isSaving={isSavingProfile}
            />
          ) : profile ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Name:</span>
                  <p className="font-medium text-gray-900 dark:text-white">{profile.name}</p>
                </div>
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Climate:</span>
                  <p className="font-medium text-gray-900 dark:text-white capitalize">{profile.climate_zone.replace('_', ' ')}</p>
                </div>
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Type:</span>
                  <p className="font-medium text-gray-900 dark:text-white capitalize">{profile.house_type.replace('_', ' ')}</p>
                </div>
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Systems:</span>
                  <p className="font-medium text-gray-900 dark:text-white">{Object.keys(profile.systems).length} devices</p>
                </div>
              </div>
              <div className="pt-2">
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  Devices: {Object.keys(profile.systems).map(d => d.replace('_', ' ')).join(', ')}
                </span>
              </div>
            </div>
          ) : (
            <p className="text-sm text-gray-500 dark:text-gray-400">
              No house profile found. Please create one to generate maintenance plans.
            </p>
          )}
        </section>

        {/* Season Selection */}
        {profile && !isEditing && (
          <section className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 sm:p-6">
            <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Select Season
            </h2>
            <div className="flex flex-wrap items-center gap-4">
              <SeasonSelector
                selected={selectedSeason}
                onSelect={setSelectedSeason}
                disabled={isLoading}
              />
              <button
                onClick={handleGeneratePlan}
                disabled={!selectedSeason || isLoading}
                className="px-4 py-2 text-sm font-medium rounded-md bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <span className="flex items-center gap-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    Generating...
                  </span>
                ) : (
                  'Generate Plan'
                )}
              </button>
            </div>
          </section>
        )}

        {/* Generated Plan */}
        {plan && !isEditing && (
          <section className="bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-4 sm:p-6">
            <ChecklistDisplay
              checklistItems={plan.checklist_items}
              markdown={plan.markdown}
              season={plan.season}
              houseName={plan.house_name}
              sourcesUsed={plan.sources_used}
              onDownloadCalendar={handleDownloadCalendar}
              isDownloadingCalendar={isDownloadingCalendar}
            />
          </section>
        )}
      </main>
    </div>
  );
}
