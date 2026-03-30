import { useEffect, useState } from "react";
import {
  getOutages,
  refreshData,
  type DataView,
  type PaginatedDataResponse,
  type GeneratorOutageItem,
  type FacilityOutageItem,
} from "./api/outages";

function App() {
  const [view, setView] = useState<DataView>("generator");
  const [date, setDate] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [sortBy, setSortBy] = useState("period_date");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  const [data, setData] = useState<PaginatedDataResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [refreshMessage, setRefreshMessage] = useState("");

  useEffect(() => {
    setPage(1);
  }, [view, date, search, pageSize]);

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

  useEffect(() => {
    let isMounted = true;

    async function loadData() {
      try {
        setIsLoading(true);
        setError("");

        const response = await getOutages({
          view,
          date: date || undefined,
          search: search || undefined,
          page,
          page_size: pageSize,
          sort_by: sortBy,
          sort_order: sortOrder,
        });

        if (isMounted) {
          setData(response);
        }
      } catch (err) {
        console.error(err);
        if (isMounted) {
          setError("Could not load outage data from the API.");
          setData(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    loadData();

    return () => {
      isMounted = false;
    };
  }, [view, date, search, page, pageSize, sortBy, sortOrder]);

  function handleSearchSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSearch(searchInput.trim());
    setPage(1);
  }

  function handleSort(column: string) {
    if (sortBy === column) {
      setSortOrder((previous) => (previous === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(column);
      setSortOrder("asc");
    }
  }

  async function handleRefresh() {
    try {
      setIsRefreshing(true);
      setRefreshMessage("");
      setError("");

      await refreshData("auto");

      setRefreshMessage("Data refresh completed successfully.");

      const response = await getOutages({
        view,
        date: date || undefined,
        search: search || undefined,
        page,
        page_size: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
      });

      setData(response);
    } catch (err) {
      console.error(err);
      setError("Could not refresh data.");
    } finally {
      setIsRefreshing(false);
    }
  }

  function renderSortIndicator(column: string) {
    if (sortBy !== column) return null;
    return sortOrder === "asc" ? " ▲" : " ▼";
  }

  const generatorItems =
    view === "generator" ? (data?.items as GeneratorOutageItem[] | undefined) : [];

  const facilityItems =
    view === "facility" ? (data?.items as FacilityOutageItem[] | undefined) : [];

  const hasItems = Boolean(data && data.items.length > 0);

  return (
    <div
      style={{
        padding: "2rem",
        fontFamily: "Arial, sans-serif",
        maxWidth: "1200px",
        margin: "0 auto",
      }}
    >
      <h1 style={{ marginBottom: "1.5rem" }}>Arkham Nuclear Outages Dashboard</h1>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: "1rem",
          marginBottom: "1.5rem",
          alignItems: "end",
        }}
      >
        <div>
          <label style={{ display: "block", marginBottom: "0.4rem" }}>View</label>
          <select
            value={view}
            onChange={(event) => setView(event.target.value as DataView)}
            style={{ width: "100%", padding: "0.5rem" }}
          >
            <option value="generator">Generator view</option>
            <option value="facility">Facility view</option>
          </select>
        </div>

        <div>
          <label style={{ display: "block", marginBottom: "0.4rem" }}>Date</label>
          <input
            type="date"
            value={date}
            onChange={(event) => setDate(event.target.value)}
            style={{ width: "100%", padding: "0.5rem" }}
          />
        </div>

        <form onSubmit={handleSearchSubmit}>
          <label style={{ display: "block", marginBottom: "0.4rem" }}>Search</label>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <input
              type="text"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Facility or generator"
              style={{ width: "100%", padding: "0.5rem" }}
            />
            <button type="submit" style={{ padding: "0.5rem 0.75rem" }}>
              Search
            </button>
          </div>
        </form>

        <div>
          <label style={{ display: "block", marginBottom: "0.4rem" }}>
            Rows per page
          </label>
          <select
            value={pageSize}
            onChange={(event) => setPageSize(Number(event.target.value))}
            style={{ width: "100%", padding: "0.5rem" }}
          >
            <option value={5}>5</option>
            <option value={10}>10</option>
            <option value={20}>20</option>
            <option value={50}>50</option>
          </select>
        </div>

        <div>
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            style={{
              width: "100%",
              padding: "0.7rem",
              fontWeight: "bold",
              cursor: isRefreshing ? "not-allowed" : "pointer",
            }}
          >
            {isRefreshing ? "Refreshing..." : "Refresh Data"}
          </button>
        </div>
      </div>

      {refreshMessage && (
        <p style={{ color: "green", marginBottom: "1rem" }}>{refreshMessage}</p>
      )}

      {error && <p style={{ color: "crimson" }}>{error}</p>}

      {isLoading && <p>Loading outage data...</p>}

      {!isLoading && !error && data && !hasItems && (
        <p>No outage records found for the selected filters.</p>
      )}

      {!isLoading && !error && data && hasItems && (
        <>
          <div style={{ marginBottom: "1rem" }}>
            <strong>Total items:</strong> {data.total_items} | <strong>Page:</strong>{" "}
            {data.page} of {data.total_pages}
          </div>

          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                background: "#fff",
                border: "1px solid #ddd",
              }}
            >
              <thead>
                <tr style={{ background: "#f4f4f4" }}>
                  <th
                    style={thStyle}
                    onClick={() => handleSort("period_date")}
                  >
                    Date{renderSortIndicator("period_date")}
                  </th>

                  <th
                    style={thStyle}
                    onClick={() => handleSort("facility_name")}
                  >
                    Facility{renderSortIndicator("facility_name")}
                  </th>

                  {view === "generator" && (
                    <>
                      <th
                        style={thStyle}
                        onClick={() => handleSort("generator_code")}
                      >
                        Generator{renderSortIndicator("generator_code")}
                      </th>
                      <th
                        style={thStyle}
                        onClick={() => handleSort("capacity_mw")}
                      >
                        Capacity MW{renderSortIndicator("capacity_mw")}
                      </th>
                      <th
                        style={thStyle}
                        onClick={() => handleSort("outage_mw")}
                      >
                        Outage MW{renderSortIndicator("outage_mw")}
                      </th>
                      <th
                        style={thStyle}
                        onClick={() => handleSort("percent_outage")}
                      >
                        % Outage{renderSortIndicator("percent_outage")}
                      </th>
                    </>
                  )}

                  {view === "facility" && (
                    <>
                      <th
                        style={thStyle}
                        onClick={() => handleSort("total_capacity_mw")}
                      >
                        Total Capacity MW{renderSortIndicator("total_capacity_mw")}
                      </th>
                      <th
                        style={thStyle}
                        onClick={() => handleSort("total_outage_mw")}
                      >
                        Total Outage MW{renderSortIndicator("total_outage_mw")}
                      </th>
                      <th
                        style={thStyle}
                        onClick={() => handleSort("percent_outage")}
                      >
                        % Outage{renderSortIndicator("percent_outage")}
                      </th>
                    </>
                  )}
                </tr>
              </thead>

              <tbody>
                {view === "generator" &&
                  generatorItems?.map((item) => (
                    <tr key={`${item.period_date}-${item.generator_id}`}>
                      <td style={tdStyle}>{item.period_date}</td>
                      <td style={tdStyle}>{item.facility_name}</td>
                      <td style={tdStyle}>{item.generator_code}</td>
                      <td style={tdStyle}>{item.capacity_mw}</td>
                      <td style={tdStyle}>{item.outage_mw}</td>
                      <td style={tdStyle}>{item.percent_outage}</td>
                    </tr>
                  ))}

                {view === "facility" &&
                  facilityItems?.map((item) => (
                    <tr key={`${item.period_date}-${item.facility_id}`}>
                      <td style={tdStyle}>{item.period_date}</td>
                      <td style={tdStyle}>{item.facility_name}</td>
                      <td style={tdStyle}>{item.total_capacity_mw}</td>
                      <td style={tdStyle}>{item.total_outage_mw}</td>
                      <td style={tdStyle}>{item.percent_outage}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>

          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginTop: "1rem",
              alignItems: "center",
            }}
          >
            <button
              onClick={() => setPage((previous) => Math.max(1, previous - 1))}
              disabled={page === 1}
              style={{ padding: "0.5rem 0.75rem" }}
            >
              Previous
            </button>

            <span>
              Page {data.page} of {data.total_pages}
            </span>

            <button
              onClick={() =>
                setPage((previous) =>
                  data ? Math.min(data.total_pages, previous + 1) : previous + 1
                )
              }
              disabled={!data || page >= data.total_pages}
              style={{ padding: "0.5rem 0.75rem" }}
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}

const thStyle: React.CSSProperties = {
  border: "1px solid #ddd",
  padding: "0.75rem",
  cursor: "pointer",
  textAlign: "left",
};

const tdStyle: React.CSSProperties = {
  border: "1px solid #ddd",
  padding: "0.75rem",
};

export default App;