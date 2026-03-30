import type {
  DataView,
  FacilityOutageItem,
  GeneratorOutageItem,
} from "@/api/outages";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
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
 * Main data table with sortable columns and contextual tooltips.
 * Tooltips explain what each metric means and hint that columns are sortable.
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

  function HeaderWithTooltip({
    column,
    label,
    description,
    align = "left",
  }: {
    column: string;
    label: string;
    description: string;
    align?: "left" | "right";
  }) {
    return (
      <TableHead
        className={`cursor-pointer ${align === "right" ? "text-right" : ""}`}
        onClick={() => onSort(column)}
      >
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="inline-flex items-center underline decoration-dotted underline-offset-4">
              {sortLabel(column, label)}
            </span>
          </TooltipTrigger>
          <TooltipContent className="max-w-xs text-sm">
            <p>{description}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Click to sort ascending or descending.
            </p>
          </TooltipContent>
        </Tooltip>
      </TableHead>
    );
  }

  return (
    <div className="overflow-x-auto rounded-2xl border bg-background">
      <Table>
        <TableHeader>
          <TableRow>
            <HeaderWithTooltip
              column="period_date"
              label="Date"
              description="The daily reporting date for the outage record."
            />

            <HeaderWithTooltip
              column="facility_name"
              label="Facility"
              description="The power plant or facility associated with the outage data."
            />

            {view === "generator" && (
              <>
                <HeaderWithTooltip
                  column="generator_code"
                  label="Generator"
                  description="The generator or unit code reported within the facility."
                />
                <HeaderWithTooltip
                  column="capacity_mw"
                  label="Capacity MW"
                  align="right"
                  description="The total generator capacity, reported in megawatts."
                />
                <HeaderWithTooltip
                  column="outage_mw"
                  label="Outage MW"
                  align="right"
                  description="The unavailable generation amount, reported in megawatts."
                />
                <HeaderWithTooltip
                  column="percent_outage"
                  label="% Outage"
                  align="right"
                  description="The percentage of unavailable generation capacity."
                />
              </>
            )}

            {view === "facility" && (
              <>
                <HeaderWithTooltip
                  column="total_capacity_mw"
                  label="Total Capacity MW"
                  align="right"
                  description="The total facility capacity across its generators, reported in megawatts."
                />
                <HeaderWithTooltip
                  column="total_outage_mw"
                  label="Total Outage MW"
                  align="right"
                  description="The total unavailable generation across the facility, reported in megawatts."
                />
                <HeaderWithTooltip
                  column="percent_outage"
                  label="% Outage"
                  align="right"
                  description="The percentage of unavailable facility capacity."
                />
              </>
            )}
          </TableRow>
        </TableHeader>

        <TableBody>
          {view === "generator" &&
            (items as GeneratorOutageItem[]).map((item) => (
              <TableRow key={`${item.period_date}-${item.generator_id}`}>
                <TableCell>{item.period_date}</TableCell>
                <TableCell>
                  <div className="flex flex-col gap-1">
                    <span>{item.facility_name}</span>
                    <span className="text-xs text-muted-foreground">
                      Facility ID: {item.facility_id}
                    </span>
                  </div>
                </TableCell>
                <TableCell>
                  <Badge variant="secondary">{item.generator_code}</Badge>
                </TableCell>
                <TableCell className="text-right">
                  {item.capacity_mw.toFixed(1)}
                </TableCell>
                <TableCell className="text-right">
                  {item.outage_mw.toFixed(1)}
                </TableCell>
                <TableCell className="text-right">
                  <Badge
                    variant={item.percent_outage > 0 ? "destructive" : "outline"}
                  >
                    {item.percent_outage.toFixed(1)}%
                  </Badge>
                </TableCell>
              </TableRow>
            ))}

          {view === "facility" &&
            (items as FacilityOutageItem[]).map((item) => (
              <TableRow key={`${item.period_date}-${item.facility_id}`}>
                <TableCell>{item.period_date}</TableCell>
                <TableCell>
                  <div className="flex flex-col gap-1">
                    <span>{item.facility_name}</span>
                    <span className="text-xs text-muted-foreground">
                      Facility ID: {item.facility_id}
                    </span>
                  </div>
                </TableCell>
                <TableCell className="text-right">
                  {item.total_capacity_mw.toFixed(1)}
                </TableCell>
                <TableCell className="text-right">
                  {item.total_outage_mw.toFixed(1)}
                </TableCell>
                <TableCell className="text-right">
                  <Badge
                    variant={item.percent_outage > 0 ? "destructive" : "outline"}
                  >
                    {item.percent_outage.toFixed(1)}%
                  </Badge>
                </TableCell>
              </TableRow>
            ))}
        </TableBody>
      </Table>
    </div>
  );
}