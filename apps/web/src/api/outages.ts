import { adminApiClient, apiClient } from "./client";

export type DataView = "generator" | "facility";
export type SortOrder = "asc" | "desc";
export type RefreshMode = "auto" | "full";

export interface GetOutagesParams {
  view: DataView;
  date?: string;
  search?: string;
  page: number;
  page_size: number;
  sort_by?: string;
  sort_order?: SortOrder;
}

export interface GeneratorOutageItem {
  period_date: string;
  generator_id: string;
  generator_code: string;
  facility_id: string;
  facility_name: string;
  capacity_mw: number;
  outage_mw: number;
  percent_outage: number;
}

export interface FacilityOutageItem {
  period_date: string;
  facility_id: string;
  facility_name: string;
  total_capacity_mw: number;
  total_outage_mw: number;
  percent_outage: number;
}

export interface PaginatedDataResponse {
  view: DataView;
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  items: GeneratorOutageItem[] | FacilityOutageItem[];
}

export interface RefreshResponse {
  status: "success";
  requested_mode: RefreshMode;
  extract: Record<string, unknown>;
  transform: Record<string, unknown>;
}

export async function getOutages(
  params: GetOutagesParams
): Promise<PaginatedDataResponse> {
  const response = await apiClient.get("/data", { params });
  return response.data;
}

export async function refreshData(
  mode: RefreshMode = "auto"
): Promise<RefreshResponse> {
  const response = await adminApiClient.post("/refresh", { mode });
  return response.data;
}