import { RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";

interface RefreshButtonProps {
  loading?: boolean;
  onRefresh: () => void;
}

/**
 * Action button that triggers backend refresh.
 */
export function RefreshButton({
  loading = false,
  onRefresh,
}: RefreshButtonProps) {
  return (
    <Button onClick={onRefresh} disabled={loading}>
      <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
      {loading ? "Refreshing..." : "Refresh Data"}
    </Button>
  );
}