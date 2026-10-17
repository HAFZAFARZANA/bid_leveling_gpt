export interface ProjectMetadata {
  project_name?: string | null;
  location?: string | null;
  bid_date?: string | null;
  budget?: number | null;
  target_budget?: number | null;
  prepared_by?: string | null;
  trade?: string | null;
}

export interface TakeoffItem {
  item_number?: string | null;
  section: string;
  original_description: string;
  model_number?: string | null;
  item_code?: string | null;
  quantity?: number | null;
  unit?: string | null;
  source_page?: number | null;
  source_evidence?: string | null;
  review_required?: boolean;
  review_reasons?: string[];
  approved?: boolean;
}

export interface SectionSummary {
  section_key: string;
  section_title: string;
  item_count: number;
  items_with_quantity: number;
  items_without_quantity: number;
  items_needing_review: number;
  items: TakeoffItem[];
}

export interface TakeoffExtractionSummary {
  total_items: number;
  total_sections: number;
  total_items_with_quantity: number;
  total_items_missing_quantity: number;
  total_review_required: number;
  total_warnings: number;
}

export interface ProposalOption {
  description: string;
  quantity?: number | null;
  unit?: string | null;
  amount?: number | null;
}

export interface PaymentScheduleItem {
  milestone: string;
  amount?: number | null;
}

export interface ProposalTerms {
  subtotal?: number | null;
  tax_rate?: number | null;
  tax_amount?: number | null;
  base_proposal_total?: number | null;
  options?: ProposalOption[];
  monitoring_rates?: ProposalOption[];
  payment_schedule?: PaymentScheduleItem[];
  notes?: string[];
  customer_responsibilities?: string[];
}

export interface TakeoffExtractionResponse {
  status: string;
  filename: string;
  total_pages_processed: number;
  project_metadata: ProjectMetadata;
  summary: TakeoffExtractionSummary;
  sections: Record<string, SectionSummary>;
  all_items: TakeoffItem[];
  warnings: string[];
  proposal_terms?: ProposalTerms | null;
  raw_model_info?: Record<string, any>;
}
