import { useMutation, useQueryClient } from "@tanstack/react-query";
import { refreshData, type RefreshMode } from "@/api/outages";

/**
 * Hook that triggers backend refresh and invalidates outage queries afterwards.
 */
export function useRefreshData() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (mode: RefreshMode) => refreshData(mode),
    onSuccess: () => {
      // After refresh finishes, refetch data queries so the UI shows updated results.
      queryClient.invalidateQueries({ queryKey: ["outages"] });
    },
  });
}