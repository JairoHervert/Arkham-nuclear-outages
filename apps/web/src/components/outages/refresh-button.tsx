import { Button } from "@/components/ui/button";

interface RefreshButtonProps {
  loading?: boolean;
  onRefresh: () => void;
}

/**
 * Button used to trigger the backend refresh pipeline.
 */
export function RefreshButton({
  loading = false,
  onRefresh,
}: RefreshButtonProps) {
  return (
    <Button onClick={onRefresh} disabled={loading} className="w-full">
      {loading ? "Refreshing..." : "Refresh Data"}
    </Button>
  );
}