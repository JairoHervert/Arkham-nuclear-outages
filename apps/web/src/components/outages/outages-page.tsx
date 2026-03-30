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

      // Explicitly reload the visible table after refresh finishes.
      const refetchResult = await outagesQuery.refetch();

      if (refetchResult.error) {
        throw refetchResult.error;
      }

      toast.success("Data refresh completed and the table was updated.", {
        id: loadingToastId,
      });
    } catch (error) {
      console.error(error);

      toast.error("Refresh finished with issues. The table could not be updated.", {
        id: loadingToastId,
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

  /**
   * Build a more precise UI state message based on the backend response.
   * We distinguish "no modeled files yet" from a generic API/server failure.
   */
  const statusInfo = useMemo(() => {
    if (refreshMutation.isError) {
      return {
        variant: "error" as const,
        title: "The refresh action failed",
        description:
          "The pipeline could not complete successfully. Please review the backend logs and try again.",
      };
    }

    if (outagesQuery.isError) {
      let backendDetail = "";

      if (axios.isAxiosError(outagesQuery.error)) {
        const detail = outagesQuery.error.response?.data?.detail;

        if (typeof detail === "string") {
          backendDetail = detail;
        }
      }

      // Special case: modeled parquet files do not exist yet.
      if (backendDetail.includes("Model parquet does not exist")) {
        return {
          variant: "missing-data" as const,
          title: "No processed outage data is available yet",
          description:
            "This dashboard does not have local modeled data yet. Use the Refresh Data button to download and build the first dataset.",
        };
      }

      return {
        variant: "error" as const,
        title: "We couldn’t load the outage data",
        description:
          "Please verify that the backend service is running, reachable, and has valid access to the required files.",
      };
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
  }, [
    refreshMutation.isError,
    outagesQuery.isError,
    outagesQuery.error,
    outagesQuery.isLoading,
    items.length,
  ]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 md:px-6 lg:px-8">
      <div className="space-y-6">
        <div className="space-y-2 text-center md:text-left">
          <h1 className="text-3xl font-bold tracking-tight md:text-4xl">
            Arkham Nuclear Outages Monitor
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
          Built by Jairo — Arkham Nuclear Outages technical challenge
        </footer>
      </div>
    </div>
  );
}