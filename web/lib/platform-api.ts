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
    review_flag: boolean;
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
  review_flag: boolean;
};

export type KnowledgeQueueResponse = {
  scanned_jobs: number;
  candidate_count: number;
  unmatched_count: number;
  review_count: number;
  candidates: KnowledgeCandidate[];
};

function apiBaseUrl() {
  return process.env.BOQ_AUTO_API_BASE_URL || "http://127.0.0.1:8080";
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    ...init,
    cache: "no-store",
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `API request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function listJobs(): Promise<Job[]> {
  return apiFetch<Job[]>("/jobs");
}

export async function getJob(jobId: string): Promise<Job> {
  return apiFetch<Job>(`/jobs/${jobId}`);
}

export async function getJobResults(jobId: string): Promise<PricingResult> {
  return apiFetch<PricingResult>(`/jobs/${jobId}/results`);
}

export async function createJob(payload: { title: string; region: string }): Promise<Job> {
  return apiFetch<Job>("/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function uploadJobFile(jobId: string, file: File, fileType = "boq"): Promise<Job> {
  const formData = new FormData();
  formData.set("file_type", fileType);
  formData.set("file", file);
  return apiFetch<Job>(`/jobs/${jobId}/files`, {
    method: "POST",
    body: formData,
  });
}

export async function priceJob(jobId: string): Promise<{ job: Job; pricing: PricingResult }> {
  return apiFetch<{ job: Job; pricing: PricingResult }>(`/jobs/${jobId}/price-boq`, {
    method: "POST",
  });
}

export async function priceCheck(query = "", limit = 50): Promise<PriceCheckResponse> {
  const params = new URLSearchParams();
  if (query.trim()) {
    params.set("q", query.trim());
  }
  params.set("limit", String(limit));
  return apiFetch<PriceCheckResponse>(`/price-check?${params.toString()}`);
}

export async function getKnowledgeQueue(limit = 50): Promise<KnowledgeQueueResponse> {
  return apiFetch<KnowledgeQueueResponse>(`/knowledge/candidates?limit=${limit}`);
}
