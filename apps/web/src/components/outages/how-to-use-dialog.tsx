import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

/**
 * Small help dialog that explains how to use the dashboard.
 * This keeps onboarding simple for reviewers.
 */
export function HowToUseDialog() {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline">How to use</Button>
      </DialogTrigger>

      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>How to use the outage monitor</DialogTitle>
          <DialogDescription>
            This dashboard lets you explore nuclear outage data from the processed
            pipeline and trigger data refresh when needed.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 text-sm leading-6 text-muted-foreground">
          <div>
            <p className="font-medium text-foreground">Generator view</p>
            <p>
              Shows one row per generator and day. Use this view when you want
              detailed outage values for individual generating units.
            </p>
          </div>

          <div>
            <p className="font-medium text-foreground">Facility view</p>
            <p>
              Aggregates generators by facility and day. Use this view when you
              want a summarized plant-level picture.
            </p>
          </div>

          <div>
            <p className="font-medium text-foreground">Sorting</p>
            <p>
              Hover over column names to read their meaning. Click a column
              header to sort ascending or descending.
            </p>
          </div>

          <div>
            <p className="font-medium text-foreground">Filters</p>
            <p>
              Use the date picker, search field, and rows-per-page selector to
              narrow results. The search works against facility and generator
              identifiers.
            </p>
          </div>

          <div>
            <p className="font-medium text-foreground">Refresh</p>
            <p>
              The refresh action triggers the backend pipeline so the dashboard
              can fetch updated data from the API and rebuild the modeled files.
            </p>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}