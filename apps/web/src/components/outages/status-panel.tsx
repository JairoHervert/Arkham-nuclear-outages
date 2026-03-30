import { AlertTriangle, DatabaseZap, FolderSearch, SearchX } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface StatusPanelProps {
  loading?: boolean;
  variant?: "error" | "empty" | "missing-data";
  title?: string;
  description?: string;
}

/**
 * Reusable centered state panel for loading, error, missing-data, and empty results.
 * The "missing-data" state is specifically useful when the backend has no modeled parquet yet.
 */
export function StatusPanel({
  loading = false,
  variant,
  title,
  description,
}: StatusPanelProps) {
  if (loading) {
    return (
      <Card className="border-dashed">
        <CardContent className="flex flex-col items-center justify-center space-y-4 py-12">
          <DatabaseZap className="h-10 w-10 text-muted-foreground" />
          <div className="space-y-2 text-center">
            <p className="text-lg font-semibold">Loading outage data</p>
            <p className="text-sm text-muted-foreground">
              Please wait while the dashboard fetches the latest records.
            </p>
          </div>

          <div className="w-full max-w-xl space-y-3">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (variant === "error") {
    return (
      <Alert variant="destructive" className="justify-center py-8 text-center">
        <div className="mx-auto flex max-w-xl flex-col items-center gap-4">
          <AlertTriangle className="h-10 w-10" />
          <div>
            <AlertTitle className="text-lg">{title}</AlertTitle>
            <AlertDescription className="mt-2 text-sm">
              {description}
            </AlertDescription>
          </div>
        </div>
      </Alert>
    );
  }

  if (variant === "missing-data") {
    return (
      <Card className="border-dashed">
        <CardContent className="flex flex-col items-center justify-center gap-4 py-12 text-center">
          <FolderSearch className="h-10 w-10 text-muted-foreground" />
          <div className="space-y-2">
            <p className="text-lg font-semibold">{title}</p>
            <p className="max-w-xl text-sm text-muted-foreground">
              {description}
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (variant === "empty") {
    return (
      <Card className="border-dashed">
        <CardContent className="flex flex-col items-center justify-center gap-4 py-12 text-center">
          <SearchX className="h-10 w-10 text-muted-foreground" />
          <div className="space-y-2">
            <p className="text-lg font-semibold">{title}</p>
            <p className="max-w-xl text-sm text-muted-foreground">
              {description}
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return null;
}