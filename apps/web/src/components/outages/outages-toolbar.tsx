import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { DataView } from "@/api/outages";
import { RefreshButton } from "./refresh-button";

interface OutagesToolbarProps {
  view: DataView;
  date: string;
  searchInput: string;
  pageSize: number;
  refreshing?: boolean;
  onViewChange: (value: DataView) => void;
  onDateChange: (value: string) => void;
  onSearchInputChange: (value: string) => void;
  onSearchSubmit: () => void;
  onClearFilters: () => void;
  onPageSizeChange: (value: number) => void;
  onRefresh: () => void;
}

/**
 * Toolbar with filters and actions for the outages dashboard.
 */
export function OutagesToolbar({
  view,
  date,
  searchInput,
  pageSize,
  refreshing = false,
  onViewChange,
  onDateChange,
  onSearchInputChange,
  onSearchSubmit,
  onClearFilters,
  onPageSizeChange,
  onRefresh,
}: OutagesToolbarProps) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
      <div className="space-y-2">
        <label className="text-sm font-medium">View</label>
        <Select value={view} onValueChange={(value) => onViewChange(value as DataView)}>
          <SelectTrigger>
            <SelectValue placeholder="Select view" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="generator">Generator view</SelectItem>
            <SelectItem value="facility">Facility view</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium">Date</label>
        <Input type="date" value={date} onChange={(e) => onDateChange(e.target.value)} />
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium">Search</label>
        <div className="flex gap-2">
          <Input
            value={searchInput}
            placeholder="Facility or generator"
            onChange={(e) => onSearchInputChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") onSearchSubmit();
            }}
          />
          <Button onClick={onSearchSubmit}>Search</Button>
        </div>
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium">Rows per page</label>
        <Select
          value={String(pageSize)}
          onValueChange={(value) => onPageSizeChange(Number(value))}
        >
          <SelectTrigger>
            <SelectValue placeholder="Rows per page" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="5">5</SelectItem>
            <SelectItem value="10">10</SelectItem>
            <SelectItem value="20">20</SelectItem>
            <SelectItem value="50">50</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="flex flex-col gap-2">
        <label className="text-sm font-medium opacity-0">Actions</label>
        <div className="flex gap-2">
          <Button variant="outline" onClick={onClearFilters} className="w-full">
            Clear filters
          </Button>
          <div className="w-full">
            <RefreshButton loading={refreshing} onRefresh={onRefresh} />
          </div>
        </div>
      </div>
    </div>
  );
}