import type {
  DataView,
  FacilityOutageItem,
  GeneratorOutageItem,
} from "@/api/outages";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface OutagesTableProps {
  view: DataView;
  items: GeneratorOutageItem[] | FacilityOutageItem[];
  sortBy: string;
  sortOrder: "asc" | "desc";
  onSort: (column: string) => void;
}

/**
 * Main data table. It changes columns depending on the selected view.
 */
export function OutagesTable({
  view,
  items,
  sortBy,
  sortOrder,
  onSort,
}: OutagesTableProps) {
  function sortLabel(column: string, label: string) {
    if (sortBy !== column) return label;
    return `${label} ${sortOrder === "asc" ? "▲" : "▼"}`;
  }

  return (
    <div className="overflow-x-auto rounded-xl border bg-background">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead
              className="cursor-pointer"
              onClick={() => onSort("period_date")}
            >
              {sortLabel("period_date", "Date")}
            </TableHead>

            <TableHead
              className="cursor-pointer"
              onClick={() => onSort("facility_name")}
            >
              {sortLabel("facility_name", "Facility")}
            </TableHead>

            {view === "generator" && (
              <>
                <TableHead
                  className="cursor-pointer"
                  onClick={() => onSort("generator_code")}
                >
                  {sortLabel("generator_code", "Generator")}
                </TableHead>
                <TableHead
                  className="cursor-pointer text-right"
                  onClick={() => onSort("capacity_mw")}
                >
                  {sortLabel("capacity_mw", "Capacity MW")}
                </TableHead>
                <TableHead
                  className="cursor-pointer text-right"
                  onClick={() => onSort("outage_mw")}
                >
                  {sortLabel("outage_mw", "Outage MW")}
                </TableHead>
                <TableHead
                  className="cursor-pointer text-right"
                  onClick={() => onSort("percent_outage")}
                >
                  {sortLabel("percent_outage", "% Outage")}
                </TableHead>
              </>
            )}

            {view === "facility" && (
              <>
                <TableHead
                  className="cursor-pointer text-right"
                  onClick={() => onSort("total_capacity_mw")}
                >
                  {sortLabel("total_capacity_mw", "Total Capacity MW")}
                </TableHead>
                <TableHead
                  className="cursor-pointer text-right"
                  onClick={() => onSort("total_outage_mw")}
                >
                  {sortLabel("total_outage_mw", "Total Outage MW")}
                </TableHead>
                <TableHead
                  className="cursor-pointer text-right"
                  onClick={() => onSort("percent_outage")}
                >
                  {sortLabel("percent_outage", "% Outage")}
                </TableHead>
              </>
            )}
          </TableRow>
        </TableHeader>

        <TableBody>
          {view === "generator" &&
            (items as GeneratorOutageItem[]).map((item) => (
              <TableRow key={`${item.period_date}-${item.generator_id}`}>
                <TableCell>{item.period_date}</TableCell>
                <TableCell>{item.facility_name}</TableCell>
                <TableCell>{item.generator_code}</TableCell>
                <TableCell className="text-right">
                  {item.capacity_mw.toFixed(1)}
                </TableCell>
                <TableCell className="text-right">
                  {item.outage_mw.toFixed(1)}
                </TableCell>
                <TableCell className="text-right">
                  {item.percent_outage.toFixed(1)}%
                </TableCell>
              </TableRow>
            ))}

          {view === "facility" &&
            (items as FacilityOutageItem[]).map((item) => (
              <TableRow key={`${item.period_date}-${item.facility_id}`}>
                <TableCell>{item.period_date}</TableCell>
                <TableCell>{item.facility_name}</TableCell>
                <TableCell className="text-right">
                  {item.total_capacity_mw.toFixed(1)}
                </TableCell>
                <TableCell className="text-right">
                  {item.total_outage_mw.toFixed(1)}
                </TableCell>
                <TableCell className="text-right">
                  {item.percent_outage.toFixed(1)}%
                </TableCell>
              </TableRow>
            ))}
        </TableBody>
      </Table>
    </div>
  );
}