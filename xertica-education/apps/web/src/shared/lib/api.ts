// Centralized API client for Xertica Education backend

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface JobState {
  id: string;
  type: string;
  status: 'queued' | 'running' | 'rendering' | 'completed' | 'failed';
  progress: number;
  created_at: string;
  updated_at: string;
  result?: any;
  error?: string | null;
}

export const api = {
  /**
   * Generic request helper
   */
  async request<T>(path: string, options?: RequestInit): Promise<T> {
    const url = `${BASE_URL.replace(/\/$/, '')}${path}`;
    const headers = {
      'Content-Type': 'application/json',
      ...(options?.headers || {}),
    };

    const res = await fetch(url, {
      ...options,
      headers,
    });

    if (!res.ok) {
      const errorText = await res.text().catch(() => 'Unknown error');
      throw new Error(`API Error [${res.status}]: ${errorText}`);
    }

    return res.json() as Promise<T>;
  },

  /**
   * Upload a Vía-2 document (multipart). No JSON Content-Type: el browser fija el boundary.
   * Por default entra a la KB (ADR-0013); `useAsSource` queda como override opcional.
   */
  async uploadDocument(
    routeId: string,
    file: File,
    useAsSource: boolean = true
  ): Promise<{ document_id: string; filename: string; use_as_source: boolean; parsed: boolean; source_id: string | null }> {
    const url = `${BASE_URL.replace(/\/$/, '')}/learning-paths/${routeId}/documents`;
    const form = new FormData();
    form.append('file', file);
    form.append('use_as_source', String(useAsSource));

    const res = await fetch(url, { method: 'POST', body: form });
    if (!res.ok) {
      const errorText = await res.text().catch(() => 'Unknown error');
      throw new Error(`API Error [${res.status}]: ${errorText}`);
    }
    return res.json();
  },

  /**
   * Create a background task orchestration job
   */
  async createJob(type: string, payload: Record<string, any> = {}): Promise<string> {
    const data = await this.request<{ id: string }>('/jobs/', {
      method: 'POST',
      body: JSON.stringify({ type, payload }),
    });
    return data.id;
  },

  /**
   * Get current job status details
   */
  async getJob(jobId: string): Promise<JobState> {
    return this.request<JobState>(`/jobs/${jobId}`);
  },

  /**
   * Poll a job until it completes or fails
   */
  async pollJob(
    jobId: string,
    onProgress?: (job: JobState) => void,
    intervalMs = 1000
  ): Promise<JobState> {
    return new Promise((resolve, reject) => {
      const runPoll = async () => {
        try {
          const job = await this.getJob(jobId);
          if (onProgress) {
            onProgress(job);
          }

          if (job.status === 'completed') {
            resolve(job);
          } else if (job.status === 'failed') {
            reject(new Error(job.error || 'Job failed'));
          } else {
            setTimeout(runPoll, intervalMs);
          }
        } catch (err) {
          reject(err);
        }
      };

      setTimeout(runPoll, intervalMs);
    });
  },
};
