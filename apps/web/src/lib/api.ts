import createClient from 'openapi-fetch';

import type { paths } from '@dar/contracts';

import { getApiBase } from './apiBase';

export const apiClient = createClient<paths>({ baseUrl: getApiBase() });

export async function fetchHealth() {
  const { data, error } = await createClient<paths>({ baseUrl: getApiBase() }).GET('/health');
  if (error) {
    throw new Error('health_request_failed');
  }
  return data;
}

export async function fetchLive() {
  const { data, error } = await createClient<paths>({ baseUrl: getApiBase() }).GET('/live');
  if (error) {
    throw new Error('live_request_failed');
  }
  return data;
}
