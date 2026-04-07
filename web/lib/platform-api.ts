export type JobFile = {
  id: number;
  file_type: string;
  filename: string;
  storage_uri: string;
  content_type: string;
  created_at: string;
};

export type JobRun = {
  id: number;
  run_type: string;
  status: string;
  processed: number;
  matched: number;
  flagged: number;
  total_cost: number;
  currency: string;
  output_storage_uri: string;
  audit_storage_uri: string;
  created_at: string;
};

export type Job = {
  id: string;
  title: string;
  region: string;
  status: string;
  created_at: string;
  updated_at: string;
  files: JobFile[];
  runs: JobRun[];
};

export type PricingResult = {
  summary: {
    currency: string;
    region: string;
    item_count: number;
    priced_item_count: number;
    matched_count: number;
    flagged_count: number;
    total_cost: number;
    average_rate: number;
  };
  items: Array<{
    description: string;
    unit: string;
    quantity: number | null;
    rate: number | null;
    amount: number | null;
    decision: string;
    matched_description: string;
    confidence_score: number;
    confidence_band: string;
    review_flag: boolean;
    flag_reasons: string[];
    generic_match_flag: boolean;
    category_mismatch_flag: boolean;
    section_mismatch_flag: boolean;
  }>;
};

export type PricingItem = PricingResult["items"][number];

export type PriceObservation = {
  job_id: string;
  job_title: string;
  region: string;
  description: string;
  matched_description: string;
  unit: string;
  rate: number;
  amount: number | null;
  decision: string;
  confidence_score: number;
  confidence_band: string;
  flag_reasons: string[];
  generic_match_flag: boolean;
  category_mismatch_flag: boolean;
  section_mismatch_flag: boolean;
};

export type PriceCheckResponse = {
  query: string;
  scanned_jobs: number;
  observed_rows: number;
  filtered_rows: number;
  average_rate: number | null;
  observations: PriceObservation[];
};

export type KnowledgeCandidate = {
  job_id: string;
  job_title: string;
  region: string;
  description: string;
  matched_description: string;
  decision: string;
  confidence_score: number;
  confidence_band: string;
  review_flag: boolean;
  flag_reasons: string[];
  generic_match_flag: boolean;
  category_mismatch_flag: boolean;
  section_mismatch_flag: boolean;
};

export type KnowledgeFocusArea = {
  label: string;
  count: number;
};

export type KnowledgeQueueResponse = {
  scanned_jobs: number;
  candidate_count: number;
  unmatched_count: number;
  review_count: number;
  focus_areas: KnowledgeFocusArea[];
  candidates: KnowledgeCandidate[];
};

export type ReviewTask = {
  id: number;
  job_id: string;
  job_run_id: number;
  status: string;
  source_row_key: string;
  sheet_name: string;
  row_number: number;
  description: string;
  matched_description: string;
  matched_item_code: string;
  task_type: string;
  task_question: string;
  response_schema: string[];
  unit: string;
  decision: string;
  confidence_score: number;
  confidence_band: string;
  flag_reasons: string[];
  reviewer_uid: string;
  reviewer_email: string;
  submitted_decision: string;
  submitted_match_description: string;
  submitted_rate: number | null;
  reviewer_note: string;
  qa_status: string;
  qa_reviewer_uid: string;
  qa_reviewer_email: string;
  qa_note: string;
  promotion_target: string;
  promotion_status: string;
  feedback_action: string;
  submitted_at: string | null;
  qa_updated_at: string | null;
  feedback_logged_at: string | null;
  created_at: string;
  updated_at: string;
};

export type ReviewTaskSyncResponse = {
  job_id: string;
  synced_count: number;
  open_count: number;
  tasks: ReviewTask[];
};

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function apiBaseUrl() {
  return process.env.NEXT_PUBLIC_BOQ_AUTO_API_BASE_URL || process.env.BOQ_AUTO_API_BASE_URL || "http://127.0.0.1:8080";
}

type ApiFetchInit = RequestInit & {
  token?: string | null;
};

async function apiFetch<T>(path: string, init?: ApiFetchInit): Promise<T> {
  const { token, headers, ...requestInit } = init ?? {};
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    ...requestInit,
    cache: "no-store",
    headers: {
      ...(headers ?? {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!response.ok) {
    const text = await response.text();
    let message = text.trim();
    try {
      const parsed = JSON.parse(text) as { detail?: string | { message?: string } };
      if (typeof parsed.detail === "string" && parsed.detail.trim()) {
        message = parsed.detail;
      } else if (parsed.detail && typeof parsed.detail === "object" && parsed.detail.message) {
        message = parsed.detail.message;
      }
    } catch {
      // Keep the raw text when the response is not JSON.
    }
    throw new ApiError(message || `API request failed: ${response.status}`, response.status);
  }
  return (await response.json()) as T;
}

export function getErrorMessage(error: unknown, fallback = "Something went wrong while talking to the API.") {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }
  return fallback;
}

export async function listJobs(token?: string | null): Promise<Job[]> {
  return apiFetch<Job[]>("/jobs", { token });
}

export async function getJob(jobId: string, token?: string | null): Promise<Job> {
  return apiFetch<Job>(`/jobs/${jobId}`, { token });
}

export async function getJobResults(jobId: string, token?: string | null): Promise<PricingResult> {
  return apiFetch<PricingResult>(`/jobs/${jobId}/results`, { token });
}

export async function createJob(payload: { title: string; region: string }, token?: string | null): Promise<Job> {
  return apiFetch<Job>("/jobs", {
    token,
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function uploadJobFile(jobId: string, file: File, fileType = "boq", token?: string | null): Promise<Job> {
  const formData = new FormData();
  formData.set("file_type", fileType);
  formData.set("file", file);
  return apiFetch<Job>(`/jobs/${jobId}/files`, {
    token,
    method: "POST",
    body: formData,
  });
}

export async function priceJob(jobId: string, token?: string | null): Promise<{ job: Job; pricing: PricingResult }> {
  return apiFetch<{ job: Job; pricing: PricingResult }>(`/jobs/${jobId}/price-boq`, {
    token,
    method: "POST",
  });
}

export async function priceCheck(query = "", limit = 50, token?: string | null): Promise<PriceCheckResponse> {
  const params = new URLSearchParams();
  if (query.trim()) {
    params.set("q", query.trim());
  }
  params.set("limit", String(limit));
  return apiFetch<PriceCheckResponse>(`/price-check?${params.toString()}`, { token });
}

export async function getKnowledgeQueue(limit = 50, token?: string | null): Promise<KnowledgeQueueResponse> {
  return apiFetch<KnowledgeQueueResponse>(`/knowledge/candidates?limit=${limit}`, { token });
}

export async function listReviewTasks(
  options?: { status?: string; qa_status?: string; promotion_status?: string; mine?: boolean },
  token?: string | null,
): Promise<ReviewTask[]> {
  const params = new URLSearchParams();
  if (options?.status) {
    params.set("status", options.status);
  }
  if (options?.qa_status) {
    params.set("qa_status", options.qa_status);
  }
  if (options?.promotion_status) {
    params.set("promotion_status", options.promotion_status);
  }
  if (options?.mine) {
    params.set("mine", "true");
  }
  const query = params.toString();
  return apiFetch<ReviewTask[]>(`/review-tasks${query ? `?${query}` : ""}`, { token });
}

export async function syncReviewTasks(jobId: string, token?: string | null): Promise<ReviewTaskSyncResponse> {
  return apiFetch<ReviewTaskSyncResponse>(`/jobs/${jobId}/review-tasks/sync`, {
    token,
    method: "POST",
  });
}

export async function claimReviewTask(taskId: number, token?: string | null): Promise<ReviewTask> {
  return apiFetch<ReviewTask>(`/review-tasks/${taskId}/claim`, {
    token,
    method: "POST",
  });
}

export async function submitReviewTask(
  taskId: number,
  payload: { decision: string; matched_description: string; rate: number | null; reviewer_note: string },
  token?: string | null,
): Promise<ReviewTask> {
  return apiFetch<ReviewTask>(`/review-tasks/${taskId}/submit`, {
    token,
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function qaReviewTask(
  taskId: number,
  payload: { qa_status: string; qa_note: string },
  token?: string | null,
): Promise<ReviewTask> {
  return apiFetch<ReviewTask>(`/review-tasks/${taskId}/qa`, {
    token,
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
