export type User = { username: string };

export type RequestItem = {
  id: number;
  request_id: string;
  submitted_date: string;
  requester_role: string;
  request_type: string;
  request_summary: string;
  priority: string;
  channel: string;
  status: string;
  missing_fields: string[];
  category: string;
  rule_matched: string;
  category_agrees: boolean;
  acknowledgement: string;
  needs_human_review: boolean;
  review_reasons: string[];
  updated_at: string | null;
};

export type Facets = {
  categories: string[];
  priorities: string[];
  statuses: string[];
  channels: string[];
  request_types: string[];
};

export type RequestList = {
  items: RequestItem[];
  total: number;
  facets: Facets;
};

export type DashboardData = {
  total: number;
  needs_review: number;
  missing: number;
  agreed: number;
  mismatched: number;
  by_category: { label: string; count: number }[];
  by_priority: { label: string; count: number }[];
  by_status: { label: string; count: number }[];
  by_channel: { label: string; count: number }[];
  review_reasons: { label: string; count: number }[];
  attention: RequestItem[];
  rules: { category: string; enabled: boolean; keywords: string[] }[];
};

export type RuleDraft = { category: string; enabled: boolean; keywords: string[] };
export type TemplateDraft = { template_key: string; body: string };
export type SettingsDraft = {
  flag_missing_fields: boolean;
  flag_category_mismatch: boolean;
  flag_high_priority: boolean;
  flag_completed: boolean;
  sensitive_keywords: string[];
  summary_min_length: number;
};
export type ListsDraft = {
  priorities: string[];
  channels: string[];
  statuses: string[];
  request_types: string[];
};
export type Policy = {
  rules: RuleDraft[];
  templates: TemplateDraft[];
  settings: SettingsDraft;
  lists: ListsDraft;
};

export type Meta = {
  priorities: string[];
  channels: string[];
  statuses: string[];
  request_types: string[];
  categories: string[];
  next_id: string;
};

export type UploadResult = {
  inserted: number;
  updated: number;
  failed: { row: number; error: string }[];
  total: number;
};
