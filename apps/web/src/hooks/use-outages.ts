import { useQuery } from "@tanstack/react-query";
import { getOutages, type GetOutagesParams } from "@/api/outages";

/**
 * Loads outage data from the backend.
 *
 * Important UX decision:
 * - disable retry to avoid repeated noisy failures when modeled files do not exist yet
 * - disable refetch on window focus/reconnect to avoid extra requests during long refresh runs
 */
export function useOutages(params: GetOutagesParams) {
  return useQuery({
    queryKey: ["outages", params],
    queryFn: () => getOutages(params),

    // Keep data stable for a short period and avoid aggressive automatic refetching.
    staleTime: 60_000,

    // Prevent automatic background refetches when returning to the browser tab.
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,

    // Avoid repeating the same failing request several times when the dataset
    // has not been built yet or when credentials are incorrect.
    retry: false,
  });
}