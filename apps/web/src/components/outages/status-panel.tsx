import type { ReactNode } from "react";
import {
  AlertTriangle,
  Database,
  DatabaseZap,
  SearchX,
  ShieldAlert,
  WifiOff,
} from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface StatusPanelProps {
  loading?: boolean;
  variant?: "error" | "empty" | "missing-data" | "auth" | "network";
  title?: ReactNode;
  description?: ReactNode;
}

/**
 * Reusable centered state panel for loading, error, missing-data, auth, network, and empty results.
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

  if (variant === "missing-data") {
    return (
      <Card className="border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/20">
        <CardContent className="flex flex-col items-center justify-center gap-4 py-12 text-center">
          <Database className="h-10 w-10 text-amber-600" />
          <div className="space-y-2">
            <p className="text-lg font-semibold text-amber-900 dark:text-amber-100">
              {title}
            </p>
            <div className="max-w-xl text-sm text-amber-800 dark:text-amber-200">
              {description}
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (variant === "auth") {
    return (
      <Card className="border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/20">
        <CardContent className="flex flex-col items-center justify-center gap-4 py-12 text-center">
          <ShieldAlert className="h-10 w-10 text-amber-600" />
          <div className="space-y-2">
            <p className="text-lg font-semibold text-amber-900 dark:text-amber-100">
              {title}
            </p>
            <div className="max-w-xl text-sm text-amber-800 dark:text-amber-200">
              {description}
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (variant === "network") {
    return (
      <Card className="border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/20">
        <CardContent className="flex flex-col items-center justify-center gap-4 py-12 text-center">
          <WifiOff className="h-10 w-10 text-amber-600" />
          <div className="space-y-2">
            <p className="text-lg font-semibold text-amber-900 dark:text-amber-100">
              {title}
            </p>
            <div className="max-w-xl text-sm text-amber-800 dark:text-amber-200">
              {description}
            </div>
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