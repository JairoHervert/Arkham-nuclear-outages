import { useQuery } from "@tanstack/react-query";
import { getOutages, type GetOutagesParams } from "@/api/outages";

/**
 * Hook that loads outage data from the backend.
 * The query key includes all filters so React Query refetches when any of them change.
 */
export function useOutages(params: GetOutagesParams) {
  return useQuery({
    queryKey: ["outages", params],
    queryFn: () => getOutages(params),
  });
}