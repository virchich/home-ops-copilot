import type {
  AskResponse,
  HouseProfile,
  MaintenancePlanResponse,
  PartsLookupRequest,
  PartsLookupResponse,
  Season,
  TroubleshootStartRequest,
  TroubleshootStartResponse,
  TroubleshootDiagnoseRequest,
  TroubleshootDiagnoseResponse,
} from '../types';

const API_URL = import.meta.env.VITE_API_URL || '/api';

export class ApiError extends Error {
  status: number;
  detail?: string;

  constructor(message: string, status: number, detail?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

export async function askQuestion(question: string): Promise<AskResponse> {
  const response = await fetch(`${API_URL}/ask`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ question }),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new ApiError(
      `Request failed with status ${response.status}`,
      response.status,
      errorBody.detail
    );
  }

  return response.json();
}

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_URL}/health`);
    return response.ok;
  } catch {
    return false;
  }
}

// =============================================================================
// MAINTENANCE PLAN API
// =============================================================================

export async function generateMaintenancePlan(season: Season): Promise<MaintenancePlanResponse> {
  const response = await fetch(`${API_URL}/maintenance-plan`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ season }),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new ApiError(
      `Request failed with status ${response.status}`,
      response.status,
      errorBody.detail
    );
  }

  return response.json();
}

/**
 * Download a .ics calendar file for the given season's maintenance plan.
 *
 * The backend runs the full maintenance workflow and converts the
 * checklist into iCalendar events. The returned blob is saved as a file.
 */
export async function downloadMaintenanceIcs(season: Season): Promise<void> {
  const response = await fetch(`${API_URL}/maintenance-plan/ics`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ season }),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new ApiError(
      `Request failed with status ${response.status}`,
      response.status,
      errorBody.detail
    );
  }

  // Download the .ics file from the response blob
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${season}-maintenance-reminders.ics`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export async function getHouseProfile(): Promise<HouseProfile> {
  const response = await fetch(`${API_URL}/house-profile`);

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new ApiError(
      `Request failed with status ${response.status}`,
      response.status,
      errorBody.detail
    );
  }

  return response.json();
}

export async function updateHouseProfile(profile: HouseProfile): Promise<HouseProfile> {
  const response = await fetch(`${API_URL}/house-profile`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(profile),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new ApiError(
      `Request failed with status ${response.status}`,
      response.status,
      errorBody.detail
    );
  }

  return response.json();
}

// =============================================================================
// TROUBLESHOOTING API
// =============================================================================

export async function startTroubleshooting(
  request: TroubleshootStartRequest
): Promise<TroubleshootStartResponse> {
  const response = await fetch(`${API_URL}/troubleshoot/start`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new ApiError(
      `Request failed with status ${response.status}`,
      response.status,
      errorBody.detail
    );
  }

  return response.json();
}

export async function submitDiagnosis(
  request: TroubleshootDiagnoseRequest
): Promise<TroubleshootDiagnoseResponse> {
  const response = await fetch(`${API_URL}/troubleshoot/diagnose`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new ApiError(
      `Request failed with status ${response.status}`,
      response.status,
      errorBody.detail
    );
  }

  return response.json();
}

// =============================================================================
// PARTS LOOKUP API
// =============================================================================

export async function lookupParts(
  request: PartsLookupRequest
): Promise<PartsLookupResponse> {
  const response = await fetch(`${API_URL}/parts/lookup`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new ApiError(
      `Request failed with status ${response.status}`,
      response.status,
      errorBody.detail
    );
  }

  return response.json();
}
