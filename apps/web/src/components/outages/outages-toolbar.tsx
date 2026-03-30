import { CalendarIcon, Search } from "lucide-react";

import type { DataView } from "@/api/outages";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { HowToUseDialog } from "./how-to-use-dialog";
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
 * Dashboard toolbar with filters and actions.
 * It uses a calendar popover instead of the native browser date input.
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
  const selectedDate = date ? new Date(`${date}T00:00:00`) : undefined;

  function formatDate(dateValue: Date | undefined) {
    if (!dateValue) return "Pick a date";
    return dateValue.toLocaleDateString();
  }

  function toIsoDate(dateValue: Date | undefined) {
    if (!dateValue) return "";
    const year = dateValue.getFullYear();
    const month = String(dateValue.getMonth() + 1).padStart(2, "0");
    const day = String(dateValue.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  return (
    <div className="space-y-4 rounded-2xl border bg-card p-4 md:p-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="space-y-1">
          <h2 className="text-xl font-semibold">Operational outage explorer</h2>
          <p className="text-sm text-muted-foreground">
            Explore outage records by generator or facility, apply filters, and
            trigger pipeline refreshes from the same interface.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <HowToUseDialog />
          <RefreshButton loading={refreshing} onRefresh={onRefresh} />
        </div>
      </div>

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
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="outline" className="w-full justify-start font-normal">
                <CalendarIcon className="mr-2 h-4 w-4" />
                {formatDate(selectedDate)}
              </Button>
            </PopoverTrigger>

            <PopoverContent className="w-auto p-0" align="start">
              <div className="space-y-2 p-2">
                <Calendar
                  mode="single"
                  selected={selectedDate}
                  onSelect={(value) => onDateChange(toIsoDate(value))}
                />

                <div className="px-2 pb-2">
                  <Button
                    variant="ghost"
                    className="w-full"
                    onClick={() => onDateChange("")}
                  >
                    Clear date
                  </Button>
                </div>
              </div>
            </PopoverContent>
          </Popover>
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
            <Button onClick={onSearchSubmit} size="icon" aria-label="Search">
              <Search className="h-4 w-4" />
            </Button>
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
              <SelectItem value="99">99</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">Reset</label>
          <Button variant="outline" onClick={onClearFilters} className="w-full">
            Clear filters
          </Button>
        </div>
      </div>
    </div>
  );
}