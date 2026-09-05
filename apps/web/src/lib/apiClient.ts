import { getApiBase } from "./apiBase";

const DEFAULT_TIMEOUT_MS = 12_000;

const DEFAULT_RETRIES = 2;



export type ApiErrorCode =
  | 'network'
  | 'timeout'
  | 'http'
  | 'parse'
  | 'service_unavailable'
  | 'unauthorized'
  | 'aborted'
  | 'catalog_corrupt';

const BACKEND_MESSAGES: Record<string, string> = {
  catalog_load_failed: 'Каталог шаблонов повреждён. Попробуйте позже или перезапустите приложение.',
  catalog_corrupt: 'Каталог шаблонов повреждён. Попробуйте позже или перезапустите приложение.',
  not_published: 'Шаблон не утверждён — заполнение недоступно.',
  source_not_approved: 'Шаблон не утверждён — заполнение недоступно.',
  font_not_ready: 'Для заполнения не хватает шрифта сервиса.',
  font_hash_mismatch: 'Для заполнения не хватает шрифта сервиса.',
  font_license_missing: 'Для заполнения не хватает шрифта сервиса.',
  font_unreadable: 'Проверьте поля формы — часть значений не подходит.',
  validation_failed: 'Проверьте поля формы — часть значений не подходит.',
  overflow: 'Проверьте поля формы — часть значений не подходит.',
  not_available: 'Генератор временно недоступен. Попробуйте позже.',
  generation_unavailable: 'Генератор временно недоступен. Попробуйте позже.',
};

function withCorrelation(message: string, correlationId?: string): string {
  if (!correlationId) return message;
  return `${message} Код обращения: ${correlationId}`;
}

export class ApiError extends Error {
  readonly code: ApiErrorCode;
  readonly status?: number | undefined;
  readonly detail?: string | undefined;
  readonly backendCode?: string | undefined;
  readonly correlationId?: string | undefined;

  constructor(
    code: ApiErrorCode,
    message: string,
    opts?: {
      status?: number | undefined;
      detail?: string | undefined;
      backendCode?: string | undefined;
      correlationId?: string | undefined;
    },
  ) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    if (opts?.status !== undefined) this.status = opts.status;
    if (opts?.detail !== undefined) this.detail = opts.detail;
    if (opts?.backendCode !== undefined) this.backendCode = opts.backendCode;
    if (opts?.correlationId !== undefined) this.correlationId = opts.correlationId;
  }

  get isConnectionError(): boolean {
    return this.code === 'network' || this.code === 'timeout' || this.code === 'service_unavailable';
  }
}

export function formatApiError(err: unknown, fallback = 'Не удалось выполнить запрос'): string {
  if (err instanceof ApiError) return err.message;
  return fallback;
}

export type ApiFetchOptions = RequestInit & {
  timeoutMs?: number;
  retries?: number;
  baseUrl?: string;
};

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function mergeAbortSignals(timeoutSignal: AbortSignal, userSignal?: AbortSignal | null): AbortSignal {
  if (!userSignal) return timeoutSignal;
  const anyFn = (AbortSignal as typeof AbortSignal & { any?: (signals: AbortSignal[]) => AbortSignal }).any;
  if (typeof anyFn === 'function') {
    return anyFn([timeoutSignal, userSignal]);
  }
  const merged = new AbortController();
  const abort = () => merged.abort();
  if (timeoutSignal.aborted || userSignal.aborted) {
    merged.abort();
    return merged.signal;
  }
  timeoutSignal.addEventListener('abort', abort, { once: true });
  userSignal.addEventListener('abort', abort, { once: true });
  return merged.signal;
}

function parseErrorBody(body: unknown): { backendCode?: string; message: string; correlationId?: string } {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (Array.isArray(detail)) {
    return { backendCode: 'validation_failed', message: BACKEND_MESSAGES.validation_failed ?? '' };
  }
  if (detail && typeof detail === 'object') {
    const rec = detail as Record<string, unknown>;
    return {
      ...(rec.code ? { backendCode: String(rec.code) } : {}),
      message: String(rec.detail || rec.message || ''),
      ...(rec.correlation_id ? { correlationId: String(rec.correlation_id) } : {}),
    };
  }
  if (typeof detail === 'string' && detail) {
    return { message: detail };
  }
  return { message: '' };
}

function errorFromResponse(status: number, body: unknown, fallback: string): ApiError {
  const parsed = parseErrorBody(body);
  const backendCode = parsed.backendCode;
  const mapped = backendCode ? BACKEND_MESSAGES[backendCode] : undefined;
  const message = mapped || parsed.message || fallback;
  const correlationId = parsed.correlationId;
  if (status === 401) {
    return new ApiError('unauthorized', 'Требуется вход', { status, backendCode, correlationId });
  }
  if (status === 503 && backendCode === 'catalog_load_failed') {
    return new ApiError('catalog_corrupt', withCorrelation(message, correlationId), {
      status,
      detail: message,
      backendCode,
      correlationId,
    });
  }
  if (status === 503) {
    return new ApiError(
      backendCode === 'font_not_ready' || backendCode === 'generation_unavailable' ? 'http' : 'service_unavailable',
      withCorrelation(
        backendCode === 'font_not_ready' ? (BACKEND_MESSAGES.font_not_ready as string) : message || 'Сервис временно недоступен',
        correlationId,
      ),
      { status, detail: message, backendCode, correlationId },
    );
  }
  return new ApiError('http', withCorrelation(message, correlationId), {
    status,
    detail: message,
    backendCode,
    correlationId,
  });
}

function shouldRetry(err: ApiError): boolean {
  if (err.code === 'unauthorized' || err.code === 'http' || err.code === 'catalog_corrupt' || err.code === 'aborted') {
    return false;
  }
  return true;
}

async function requestOnce(url: string, options: ApiFetchOptions, timeoutMs: number, accept: string): Promise<Response> {
  const timeoutController = new AbortController();
  const timer = setTimeout(() => timeoutController.abort(), timeoutMs);
  const { timeoutMs: _timeout, retries: _retries, baseUrl: _base, ...init } = options;
  try {
    return await fetch(url, {
      ...init,
      credentials: init.credentials ?? 'include',
      signal: mergeAbortSignals(timeoutController.signal, init.signal ?? null),
      headers: {
        Accept: accept,
        ...(init.headers ?? {}),
      },
    });
  } finally {
    clearTimeout(timer);
  }
}

export async function apiFetch<T = unknown>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const baseUrl = (options.baseUrl ?? getApiBase()).replace(/\/$/, '');
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const retries = options.retries ?? DEFAULT_RETRIES;
  const url = path.startsWith('http') ? path : `${baseUrl}${path.startsWith('/') ? path : `/${path}`}`;
  let lastError: ApiError | null = null;

  for (let attempt = 0; attempt <= retries; attempt += 1) {
    try {
      const res = await requestOnce(url, options, timeoutMs, 'application/json');
      if (!res.ok) {
        let body: unknown = null;
        try {
          body = await res.json();
        } catch {
          body = null;
        }
        throw errorFromResponse(res.status, body, res.statusText || 'Ошибка запроса');
      }
      if (res.status === 204) {
        return undefined as T;
      }
      const contentType = res.headers.get('content-type') ?? '';
      if (!contentType.includes('application/json')) {
        return (await res.text()) as T;
      }
      return (await res.json()) as T;
    } catch (err) {
      if (err instanceof ApiError) {
        lastError = err;
        if (!shouldRetry(err) || attempt >= retries) throw err;
      } else if (err instanceof DOMException && err.name === 'AbortError') {
        if (options.signal?.aborted) {
          throw new ApiError('aborted', 'Запрос отменён');
        }
        lastError = new ApiError('timeout', 'Превышено время ожидания ответа');
      } else {
        lastError = new ApiError('network', 'Не удалось связаться с сервисом');
      }
      if (attempt < retries) {
        await sleep(250 * (attempt + 1));
        continue;
      }
    }
  }

  throw lastError ?? new ApiError('network', 'Не удалось связаться с сервисом');
}

async function apiDownload(path: string, options: ApiFetchOptions = {}): Promise<Blob> {
  const baseUrl = (options.baseUrl ?? getApiBase()).replace(/\/$/, '');
  const timeoutMs = options.timeoutMs ?? 20_000;
  const retries = options.retries ?? DEFAULT_RETRIES;
  const url = path.startsWith('http') ? path : `${baseUrl}${path.startsWith('/') ? path : `/${path}`}`;
  let lastError: ApiError | null = null;

  for (let attempt = 0; attempt <= retries; attempt += 1) {
    try {
      const res = await requestOnce(url, options, timeoutMs, 'application/pdf, application/json');
      if (!res.ok) {
        let body: unknown = null;
        try {
          body = await res.json();
        } catch {
          body = null;
        }
        throw errorFromResponse(res.status, body, res.statusText || 'Ошибка скачивания');
      }
      return await res.blob();
    } catch (err) {
      if (err instanceof ApiError) {
        lastError = err;
        if (!shouldRetry(err) || attempt >= retries) throw err;
      } else if (err instanceof DOMException && err.name === 'AbortError') {
        if (options.signal?.aborted) {
          throw new ApiError('aborted', 'Запрос отменён');
        }
        lastError = new ApiError('timeout', 'Превышено время ожидания скачивания');
      } else {
        lastError = new ApiError('network', 'Не удалось скачать файл');
      }
      if (attempt < retries) {
        await sleep(250 * (attempt + 1));
        continue;
      }
    }
  }

  throw lastError ?? new ApiError('network', 'Не удалось скачать файл');
}



export type DocumentListItem = {

  id: string;

  state: string;

  display_name: string;

  detected_type: string | null;

  updated_at: string;

  latest_run_id: string | null;

  latest_run_status: string | null;

};



export type DocumentDetail = {

  id: string;

  state: string;

  display_name: string;

  detected_type: string | null;

  error_code: string | null;

  created_at: string;

};



export type Citation = { page: number; bbox: { x: number; y: number; w: number; h: number }; quote: string };



export type AnalysisFinding = {

  id: string;

  kind: string;

  entity_type: string;

  raw_text: string;

  normalized_value: unknown;

  confidence: number;

  uncertainty_state: string;

  citation: Citation;

};



export type RuleHit = {

  rule_id: string;

  rule_version: string;

  result_kind: string;

  severity: string;

  severity_rationale: string;

  message: string;

  uncertainty: string;

  citations: Citation[];

  basis_fact_keys: string[];

  official_sources: string[];

};



export type AnalysisRun = {

  id: string;

  document_id: string;

  status: string;

  error_code: string | null;

  llm_available?: boolean;

  local_steps?: string[];

  findings: AnalysisFinding[];

  rule_hits: RuleHit[];

  pages: Array<{

    page_number: number;

    width: number;

    height: number;

    rotation: number;

    confidence: number;

    language: string;

    source: string;

    error_code: string | null;

    layout_region_types: string[];

  }>;

  progress: Array<{ stage: string; percent: number; error_code?: string | null }>;

};



export type CompareDiffItem = {

  change: string;

  path: string;

  left_citation: Citation | null;

  right_citation: Citation | null;

  left_text: string | null;

  right_text: string | null;

};



export type CompareResult = {

  left_document_id: string;

  right_document_id: string;

  party_diffs: CompareDiffItem[];

  section_diffs: CompareDiffItem[];

  clause_diffs: CompareDiffItem[];

  refused: boolean;

  refusal_reason: string | null;

};



export type UploadLimits = {

  max_bytes: number;

  max_pages: number;

  allowed_extensions: string[];

  formats_label: string;

};



export async function fetchDocuments(): Promise<DocumentListItem[]> {

  return apiFetch<DocumentListItem[]>('/documents');

}



export async function fetchAnalysisRun(runId: string): Promise<AnalysisRun> {

  return apiFetch<AnalysisRun>(`/analysis/runs/${runId}`);

}



export async function fetchAnalysisProgress(runId: string) {

  return apiFetch<Array<{ stage: string; percent: number; page?: number | null; error_code?: string | null }>>(

    `/analysis/runs/${runId}/progress`,

  );

}



export async function fetchUploadLimits(): Promise<UploadLimits> {

  return apiFetch<UploadLimits>('/documents/upload-limits');

}



export async function startAnalysis(documentId: string) {

  return apiFetch<{ run_id: string; status: string }>('/analysis/runs', {

    method: 'POST',

    headers: { 'Content-Type': 'application/json' },

    body: JSON.stringify({ document_id: documentId, fixture_id: null }),

  });

}



export async function retryAnalysis(runId: string, stage = 'analysis') {

  return apiFetch<{ run_id: string; status: string }>(`/analysis/runs/${runId}/retry`, {

    method: 'POST',

    headers: { 'Content-Type': 'application/json' },

    body: JSON.stringify({ stage }),

  });

}



export async function fetchDocumentRuns(documentId: string) {

  return apiFetch<Array<{ run_id: string; status: string }>>(`/analysis/documents/${documentId}/runs`);

}



export async function fetchPublicConfig() {

  return apiFetch<{ demo_mode: boolean; max_analysis_pages: number }>('/config/public');

}



export async function fetchDocument(documentId: string): Promise<DocumentDetail> {

  return apiFetch<DocumentDetail>(`/documents/${documentId}`);

}



export async function deleteDocument(documentId: string): Promise<DocumentDetail> {

  return apiFetch<DocumentDetail>(`/documents/${documentId}`, { method: 'DELETE' });

}



export async function compareDocuments(documentIds: string[]): Promise<CompareResult> {

  return apiFetch<CompareResult>('/reports/compare/documents', {

    method: 'POST',

    headers: { 'Content-Type': 'application/json' },

    body: JSON.stringify({ document_ids: documentIds }),

  });

}



export type FeedbackKind = 'useful' | 'error' | 'bad_citation';



export async function submitFeedback(payload: {

  target_type: 'finding' | 'rule_hit' | 'report';

  target_id: string;

  kind: FeedbackKind;

  comment?: string;

}) {

  return apiFetch<{ id: string; message: string }>('/reports/feedback', {

    method: 'POST',

    headers: { 'Content-Type': 'application/json' },

    body: JSON.stringify(payload),

  });

}



export async function exportAnalysisRun(runId: string, format: 'pdf' | 'json'): Promise<Blob> {

  return apiDownload('/reports/export/run', {

    method: 'POST',

    headers: { 'Content-Type': 'application/json', Accept: '*/*' },

    body: JSON.stringify({ analysis_run_id: runId, format }),

  });

}



export async function downloadDocumentDerived(documentId: string): Promise<Blob> {
  return apiDownload(`/documents/${documentId}/download`);
}

export type FormCard = {
  id: string;
  slug: string;
  title: string;
  organ: string;
  status: string;
  edition: string;
  warning: string;
  category: string;
  category_label: string;
  form_kind: string;
  fill_ready: boolean;
  worksheet_ready?: boolean;
  official_url?: string | null;
  act_title?: string | null;
  unavailable_reason: string | null;
};

export async function fetchForms(query = '', signal?: AbortSignal): Promise<FormCard[]> {
  const data = await apiFetch<FormCard[]>(`/forms${query}`, signal ? { signal, retries: 0 } : { retries: DEFAULT_RETRIES });
  if (!Array.isArray(data)) {
    throw new ApiError('catalog_corrupt', 'Каталог шаблонов повреждён.');
  }
  return data;
}



export type GenerationCapabilities = {
  catalog_ready: boolean;
  fill_engine_ready: boolean;
  font_ready: boolean;
  official_templates_count: number;
  generation_ready: boolean;
  medical_memo_ready?: boolean;
  reasons: string[];
  font_reason?: string;
};

export async function fetchGenerationCapabilities(): Promise<GenerationCapabilities> {
  return apiFetch<GenerationCapabilities>('/capabilities');
}

function filenameFromDisposition(header: string | null, fallback: string): string {
  if (!header) return fallback;
  const star = /filename\*=UTF-8''([^;]+)/i.exec(header);
  if (star?.[1]) {
    try {
      return decodeURIComponent(star[1]);
    } catch {
      return fallback;
    }
  }
  const simple = /filename="?([^";]+)"?/i.exec(header);
  return simple?.[1] || fallback;
}

export async function downloadGeneratedPdf(generatedId: string): Promise<{ blob: Blob; filename: string }> {
  const baseUrl = getApiBase().replace(/\/$/, '');
  const url = `${baseUrl}/forms/fill/generated/${generatedId}/pdf`;
  let lastError: ApiError | null = null;
  for (let attempt = 0; attempt <= DEFAULT_RETRIES; attempt += 1) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 20_000);
    try {
      const res = await fetch(url, {
        credentials: 'include',
        signal: controller.signal,
        headers: { Accept: 'application/pdf' },
      });
      clearTimeout(timer);
      if (!res.ok) {
        let detail = res.statusText;
        try {
          const body = await res.json();
          detail = body?.detail?.detail ?? body?.detail ?? detail;
        } catch {
          // ignore
        }
        throw new ApiError('http', String(detail || `HTTP ${res.status}`), { status: res.status, detail: String(detail) });
      }
      const blob = await res.blob();
      const filename = filenameFromDisposition(res.headers.get('content-disposition'), `document.pdf`);
      return { blob, filename };
    } catch (err) {
      clearTimeout(timer);
      if (err instanceof ApiError) {
        lastError = err;
        if (err.code === 'unauthorized' || err.code === 'http') throw err;
      } else if (err instanceof DOMException && err.name === 'AbortError') {
        lastError = new ApiError('timeout', 'Превышено время ожидания скачивания');
      } else {
        lastError = new ApiError('network', 'Не удалось скачать файл');
      }
      if (attempt < DEFAULT_RETRIES) {
        await sleep(250 * (attempt + 1));
        continue;
      }
    }
  }
  throw lastError ?? new ApiError('network', 'Не удалось скачать файл');
}



export async function exportEntryChecklistPdf(snapshotId: string): Promise<Blob> {
  return apiDownload(`/entry/snapshots/${snapshotId}/checklist.pdf`, {
    method: 'POST',
    retries: 1,
  });
}

export async function fetchVisaRegimes(): Promise<Array<{ id: string; label: string; source_slug: string }>> {
  const data = await apiFetch<Array<{ id: string; label: string; source_slug: string }>>('/entry/visa-regimes');
  if (!Array.isArray(data)) {
    throw new ApiError('parse', 'Не удалось загрузить список визовых режимов');
  }
  return data;
}

export async function checkApiLive(): Promise<boolean> {
  try {
    await apiFetch('/live', { retries: 0, timeoutMs: 3000 });
    return true;
  } catch {
    return false;
  }
}



export function downloadBlob(blob: Blob, filename: string) {

  const url = URL.createObjectURL(blob);

  const a = document.createElement('a');

  a.href = url;

  a.download = filename;

  a.click();

  URL.revokeObjectURL(url);

}



export function buildAnalyzerDocumentUrl(documentId: string, runId?: string | null) {

  const params = new URLSearchParams({ tab: 'documents', document: documentId });

  if (runId) params.set('run', runId);

  return `/app/analyzer?${params.toString()}`;

}


