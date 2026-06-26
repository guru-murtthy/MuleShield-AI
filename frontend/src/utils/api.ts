import axios from 'axios';
import type { AlertsResponse, ActionResponse, HealthResponse, ScoreResponse } from '../types';

const BASE = '/api/v1';

export const api = axios.create({ baseURL: BASE, timeout: 10000 });

export async function fetchHealth(): Promise<HealthResponse> {
  const { data } = await api.get<HealthResponse>('/health');
  return data;
}

export async function fetchAlerts(page = 1, page_size = 20, risk_band?: string): Promise<AlertsResponse> {
  const params: Record<string, string | number> = { page, page_size };
  if (risk_band) params.risk_band = risk_band;
  const { data } = await api.get<AlertsResponse>('/alerts', { params });
  return data;
}

export async function scoreAccount(account_id: string, features: number[]): Promise<ScoreResponse> {
  const { data } = await api.post<ScoreResponse>('/score', { account_id, features });
  return data;
}

export async function applyAction(
  account_id: string,
  action_type: string,
  analyst_id = 'dashboard_user'
): Promise<ActionResponse> {
  const { data } = await api.post<ActionResponse>('/action', { account_id, action_type, analyst_id });
  return data;
}
