import type {
  AskResponse,
  HouseProfile,
  MaintenancePlanResponse,
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
