import { useEffect, useState } from "react";
import type { DataView } from "@/api/outages";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useOutages } from "@/hooks/use-outages";
import { useRefreshData } from "@/hooks/use-refresh-data";
import { OutagesTable } from "./outages-table";
import { OutagesToolbar } from "./outages-toolbar";
import { PaginationControls } from "./pagination-controls";
import { StatusPanel } from "./status-panel";

/**
 * Main page container for the outages dashboard.
 * It holds the state for filters, sorting, pagination, and refresh.
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
  const [refreshMessage, setRefreshMessage] = useState("");

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

  // Whenever filters change, go back to the first page.
  useEffect(() => {
    setPage(1);
  }, [view, date, search, pageSize]);

  // Ensure sort columns stay valid for the selected view.
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

  async function handleRefresh() {
    try {
      setRefreshMessage("");
      await refreshMutation.mutateAsync("auto");
      setRefreshMessage("Data refresh completed successfully.");
    } catch {
      // Error is already surfaced by the mutation state.
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

  return (
    <div className="mx-auto max-w-7xl p-6">
      <Card className="border-0 shadow-none">
        <CardHeader className="px-0">
          <CardTitle className="text-3xl">Arkham Nuclear Outages Dashboard</CardTitle>
        </CardHeader>

        <CardContent className="space-y-6 px-0">
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

          {refreshMessage && (
            <p className="text-sm text-green-600">{refreshMessage}</p>
          )}

          <StatusPanel
            loading={outagesQuery.isLoading}
            error={
              refreshMutation.isError
                ? "Could not refresh data."
                : outagesQuery.isError
                ? "Could not load outage data from the API."
                : undefined
            }
            empty={!outagesQuery.isLoading && !outagesQuery.isError && items.length === 0}
          />

          {!outagesQuery.isLoading && !outagesQuery.isError && items.length > 0 && data && (
            <>
              <div className="text-sm text-muted-foreground">
                Total items: {data.total_items} · Page {data.page} of {data.total_pages}
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
    </div>
  );
}