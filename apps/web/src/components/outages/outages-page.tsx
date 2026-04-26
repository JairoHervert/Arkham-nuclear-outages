import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import axios from "axios";

import type { DataView } from "@/api/outages";
import { Card, CardContent } from "@/components/ui/card";
import { useOutages } from "@/hooks/use-outages";
import { useRefreshData } from "@/hooks/use-refresh-data";
import { OutagesTable } from "./outages-table";
import { OutagesToolbar } from "./outages-toolbar";
import { PaginationControls } from "./pagination-controls";
import { StatusPanel } from "./status-panel";

/**
 * Small helper that extracts useful API error information from an Axios error.
 */
function parseApiError(error: unknown) {
  if (!axios.isAxiosError(error)) {
    return {
      status: undefined as number | undefined,
      detail: "",
      isNetworkError: false,
    };
  }

  const status = error.response?.status;
  const payload = error.response?.data;

  let detail = "";
  if (typeof payload?.detail === "string") {
    detail = payload.detail;
  }

  return {
    status,
    detail,
    isNetworkError: !error.response,
  };
}

/**
 * Maps /data query failures into friendly UI states.
 */
function buildDataStatus(error: unknown) {
  const { status, detail, isNetworkError } = parseApiError(error);

  if (detail.includes("Model parquet does not exist")) {
    return {
      variant: "missing-data" as const,
      title: "No processed outage data is available yet",
      description: (
        <>
          This dashboard still has no local modeled dataset.
          <br />
          <strong>Click the “Refresh Data” button</strong> to download and build
          the data for the first time.
        </>
      ),
    };
  }

  if (status === 401 || status === 403) {
    return {
      variant: "auth" as const,
      title: "The API key is not valid for data access",
      description:
        "The configured read access key is not valid. Please review the frontend environment configuration.",
    };
  }

  if (isNetworkError) {
    return {
      variant: "network" as const,
      title: "We couldn’t reach the backend API",
      description:
        "Please verify the frontend API configuration and confirm that the backend service is running.",
    };
  }

  return {
    variant: "error" as const,
    title: "We couldn’t load the outage data",
    description:
      "The API returned an unexpected error. Please review the backend logs and try again.",
  };
}

/**
 * Maps refresh failures into friendly toast messages.
 */
function buildRefreshFeedback(error: unknown) {
  const { status, detail, isNetworkError } = parseApiError(error);

  if (detail.includes("Could not authenticate with EIA")) {
    return {
      title: "The EIA API key is not valid",
      description:
        "The backend could not authenticate with the EIA API. Please verify the server-side EIA credentials and try again.",
    };
  }

  if (status === 401 || status === 403) {
    return {
      title: "Refresh is not authorized",
      description:
        "The configured admin access key is not valid. Please review the frontend environment configuration.",
    };
  }

  if (isNetworkError) {
    return {
      title: "Refresh could not reach the backend API",
      description:
        "Please verify the frontend API configuration and confirm that the backend service is running.",
    };
  }

  return {
    title: "Refresh finished with issues",
    description:
      "The pipeline or the table update did not complete successfully. Please review the backend logs.",
  };
}

/**
 * Main page container for the outages dashboard.
 * Handles filtering, sorting, pagination, and refresh state.
 */
export function OutagesPage() {
  const [view, setView] = useState<DataView>("generator");
  const [date, setDate] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [sortBy, setSortBy] = useState("period_date");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  const outagesQuery = useOutages({
    view,
    date: date || undefined,
    search: search || undefined,
    page,
    page_size: pageSize,
    sort_by: sortBy,
    sort_order: sortOrder,
  });

  const refreshMutation = useRefreshData();

  // When filters change, the current page resets to the first page.
  useEffect(() => {
    setPage(1);
  }, [view, date, search, pageSize]);

  // Keep sorting compatible with the selected view.
  useEffect(() => {
    if (view === "generator") {
      if (sortBy === "total_capacity_mw" || sortBy === "total_outage_mw") {
        setSortBy("period_date");
      }
    } else {
      if (
        sortBy === "generator_id" ||
        sortBy === "generator_code" ||
        sortBy === "capacity_mw" ||
        sortBy === "outage_mw"
      ) {
        setSortBy("period_date");
      }
    }
  }, [view, sortBy]);

  /**
   * Trigger backend refresh and then explicitly refetch the visible table data.
   * The success toast should appear only if both operations succeed.
   */
  async function handleRefresh() {
    const loadingToastId = toast.loading("Refreshing pipeline data...");

    try {
      await refreshMutation.mutateAsync("auto");

      const refetchResult = await outagesQuery.refetch();

      if (refetchResult.error) {
        throw refetchResult.error;
      }

      toast.success("Data refresh completed successfully.", {
        id: loadingToastId,
        description: "The pipeline finished and the table was updated.",
      });
    } catch (error) {
      console.error(error);

      const feedback = buildRefreshFeedback(error);

      toast.error(feedback.title, {
        id: loadingToastId,
        description: feedback.description,
      });
    }
  }

  function handleSearchSubmit() {
    setSearch(searchInput.trim());
    setPage(1);
  }

  function handleClearFilters() {
    setView("generator");
    setDate("");
    setSearchInput("");
    setSearch("");
    setPage(1);
    setPageSize(10);
    setSortBy("period_date");
    setSortOrder("desc");
  }

  function handleSort(column: string) {
    if (sortBy === column) {
      setSortOrder((previous) => (previous === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(column);
      setSortOrder("asc");
    }
  }

  const data = outagesQuery.data;
  const items = data?.items ?? [];

  const statusInfo = useMemo(() => {
    if (outagesQuery.isError) {
      return buildDataStatus(outagesQuery.error);
    }

    if (!outagesQuery.isLoading && items.length === 0) {
      return {
        variant: "empty" as const,
        title: "No matching outage records",
        description:
          "Try changing the selected date, search text, or view to broaden the results.",
      };
    }

    return null;
  }, [outagesQuery.isError, outagesQuery.error, outagesQuery.isLoading, items.length]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 md:px-6 lg:px-8">
      <div className="space-y-6">
        <div className="space-y-2 text-center md:text-left">
          <h1 className="text-3xl font-bold tracking-tight md:text-4xl">
            EIA Nuclear Outages Monitor
          </h1>
          <p className="mx-auto max-w-3xl text-sm text-muted-foreground md:mx-0 md:text-base">
            Explore modeled outage data from the pipeline, compare generator and
            facility views, apply filters, and trigger refreshes from the same
            interface.
          </p>
        </div>

        <OutagesToolbar
          view={view}
          date={date}
          searchInput={searchInput}
          pageSize={pageSize}
          refreshing={refreshMutation.isPending}
          onViewChange={setView}
          onDateChange={setDate}
          onSearchInputChange={setSearchInput}
          onSearchSubmit={handleSearchSubmit}
          onClearFilters={handleClearFilters}
          onPageSizeChange={setPageSize}
          onRefresh={handleRefresh}
        />

        <Card className="rounded-2xl">
          <CardContent className="space-y-6 p-4 md:p-6">
            <StatusPanel
              loading={outagesQuery.isLoading}
              variant={statusInfo?.variant}
              title={statusInfo?.title}
              description={statusInfo?.description}
            />

            {!outagesQuery.isLoading &&
              !outagesQuery.isError &&
              items.length > 0 &&
              data && (
                <>
                  <div className="flex flex-col gap-2 text-sm text-muted-foreground md:flex-row md:items-center md:justify-between">
                    <span>Total items: {data.total_items}</span>
                    <span>
                      Showing page {data.page} of {data.total_pages}
                    </span>
                  </div>

                  <OutagesTable
                    view={view}
                    items={items}
                    sortBy={sortBy}
                    sortOrder={sortOrder}
                    onSort={handleSort}
                  />

                  <PaginationControls
                    page={data.page}
                    totalPages={data.total_pages}
                    onPrevious={() => setPage((previous) => Math.max(1, previous - 1))}
                    onNext={() =>
                      setPage((previous) => Math.min(data.total_pages, previous + 1))
                    }
                  />
                </>
              )}
          </CardContent>
        </Card>

        <footer className="pb-4 text-center text-xs text-muted-foreground">
          Built by Jairo — Personal data engineering project
        </footer>
      </div>
    </div>
  );
}