import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

const ALL_LANES = [
  "Application / Review",
  "Pending (no issues)",
  "Ready to Issue",
  "Permit Issued (Inspection)",
  "Pending CO",
  "Closed",
  "TCO Issued",
  "Permit Expired",
  "Unrecognized",
];

const DEFAULT_VISIBLE_LANES = [
  "Application / Review",
  "Pending (no issues)",
  "Ready to Issue",
  "Permit Issued (Inspection)",
  "Closed",
];

const LANE_DISPLAY: Record<string, string> = {
  "Application / Review": "Application / Review",
  "Pending (no issues)": "Pending",
  "Ready to Issue": "Ready to Issue",
  "Permit Issued (Inspection)": "Inspection",
  "Pending CO": "Pending CO",
  "Closed": "Closed",
  "TCO Issued": "TCO Issued",
  "Permit Expired": "Permit Expired",
  "Unrecognized": "Unrecognized",
};

const LANE_COLOR: Record<string, string> = {
  "Application / Review": "#1a56db",
  "Pending (no issues)": "#f5a623",
  "Ready to Issue": "#0e9f6e",
  "Permit Issued (Inspection)": "#7c3aed",
  "Pending CO": "#ec4899",
  "Closed": "#64748b",
  "TCO Issued": "#06b6d4",
  "Permit Expired": "#b91c1c",
  "Unrecognized": "#9ca3af",
};

const CLOSED_SUBS = ["Closed - Complete", "Closed - Approved", "Closed - Issued", "Closed - Withdrawn"];

interface Permit {
  record_number: string;
  address: string;
  current_status: string;
  current_milestone: string;
  changed: boolean;
  change_info?: {
    from_status: string;
    to_status: string;
    is_backward: boolean;
    is_tracked_milestone: boolean;
  };
}

export function KanbanBoard({
  data,
  selectedTransition,
  legendFilter,
  onLegendFilter,
}: {
  data: {
    columns: { milestone: string; permits: Permit[] }[];
    closed_sub_statuses?: Record<string, number>;
  };
  selectedTransition: { from: string; to: string } | null;
  legendFilter: "changed" | "tracked" | "backward" | null;
  onLegendFilter: (filter: "changed" | "tracked" | "backward" | null) => void;
}) {
  const [dialogPermit, setDialogPermit] = useState<string | null>(null);
  const [visibleLanes, setVisibleLanes] = useState<string[]>(DEFAULT_VISIBLE_LANES);
  const [expandedLane, setExpandedLane] = useState<string | null>(null);
  const [showLaneEditor, setShowLaneEditor] = useState(false);
  const [closedTab, setClosedTab] = useState<string | null>(null);

  const columns = data.columns || [];
  const closedSubStatuses = data.closed_sub_statuses || {};

  const handleShowTimeline = async (recordNumber: string) => {
    setDialogPermit(recordNumber);
  };

  const toggleLane = (lane: string) => {
    setVisibleLanes((prev) =>
      prev.includes(lane) ? prev.filter((l) => l !== lane) : [...prev, lane]
    );
    if (lane === "Closed" && visibleLanes.includes("Closed")) {
      setClosedTab(null);
    }
  };

  const filteredColumns = columns
    .filter((col) => visibleLanes.includes(col.milestone))
    .map((col) => {
      let permits = col.permits;

      if (col.milestone === "Closed" && closedTab) {
        permits = permits.filter((p) => p.current_status === closedTab);
      }

      if (selectedTransition) {
        permits = permits.filter((p) => {
          if (!p.changed || !p.change_info) return false;
          return (
            p.change_info.from_status === selectedTransition.from &&
            p.change_info.to_status === selectedTransition.to
          );
        });
      }

      if (legendFilter) {
        permits = permits.filter((p) => {
          if (!p.changed || !p.change_info) return false;
          if (legendFilter === "backward") return p.change_info.is_backward;
          if (legendFilter === "tracked") return p.change_info.is_tracked_milestone;
          if (legendFilter === "changed") return !p.change_info.is_backward && !p.change_info.is_tracked_milestone;
          return false;
        });
      }

      return { ...col, permits };
    });

  const legendItems: { key: "changed" | "tracked" | "backward"; label: string; dotClass: string }[] = [
    { key: "changed", label: "Changed", dotClass: "bg-blue-500" },
    { key: "tracked", label: "Tracked milestone", dotClass: "bg-purple-500" },
    { key: "backward", label: "Backward", dotClass: "bg-red-500" },
  ];

  return (
    <div className="space-y-5">
      {/* Clickable legend */}
      <div className="flex items-center gap-5">
        <span className="text-[10px] font-medium text-gray-400 uppercase tracking-wide">
          Legend
        </span>
        {legendItems.map((item) => {
          const isActive = legendFilter === item.key;
          return (
            <button
              key={item.key}
              onClick={() => onLegendFilter(isActive ? null : item.key)}
              className={`inline-flex items-center gap-1.5 text-[10px] transition-all duration-200 px-2 py-1 rounded-full border ${
                isActive
                  ? "bg-gray-900 text-white border-gray-900 shadow-sm"
                  : "text-gray-500 border-gray-200 hover:border-gray-300 hover:bg-gray-50"
              }`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${item.dotClass}`} />
              {item.label}
            </button>
          );
        })}
        {legendFilter && (
          <button
            onClick={() => onLegendFilter(null)}
            className="text-[10px] text-gray-400 hover:text-gray-600 underline underline-offset-2 transition-colors"
          >
            Clear
          </button>
        )}
      </div>

      {/* Subtle divider */}
      <div className="h-px bg-gray-200/60" />

      {/* Lane customize: arrow toggle + colored lines / pills */}
      <div className="relative">
        {/* Collapse/expand arrow */}
        <div className="flex items-center gap-2 mb-2">
          <button
            onClick={() => setShowLaneEditor(!showLaneEditor)}
            className="text-[10px] text-gray-400 hover:text-gray-600 transition-colors flex items-center gap-1"
          >
            <span
              className={`inline-block transition-transform duration-200 ${
                showLaneEditor ? "rotate-90" : ""
              }`}
            >
              ▶
            </span>
            {showLaneEditor ? "Hide lanes" : `${visibleLanes.length} lanes`}
          </button>
        </div>

        {/* Collapsed: thin colored lines */}
        <div
          className={`flex gap-1.5 transition-all duration-300 ${
            showLaneEditor ? "opacity-0 h-0 overflow-hidden" : "opacity-100 h-4"
          }`}
        >
          {visibleLanes.map((lane) => (
            <div
              key={lane}
              className="border-t-2 rounded-sm"
              style={{
                borderColor: LANE_COLOR[lane],
                minWidth: "60px",
                flex: "1 1 0%",
                maxWidth: "120px",
              }}
            />
          ))}
        </div>

        {/* Expanded: colored lane pills */}
        <div
          className={`flex flex-wrap gap-1.5 transition-all duration-300 ${
            showLaneEditor ? "opacity-100 max-h-40" : "opacity-0 max-h-0 overflow-hidden"
          }`}
        >
          {ALL_LANES.map((lane) => (
            <button
              key={lane}
              onClick={() => toggleLane(lane)}
              className="text-[10px] px-2 py-1 rounded border transition-all duration-200"
              style={{
                backgroundColor: visibleLanes.includes(lane)
                  ? `${LANE_COLOR[lane]}15`
                  : "#f9fafb",
                borderColor: visibleLanes.includes(lane)
                  ? `${LANE_COLOR[lane]}40`
                  : "#e5e7eb",
                color: visibleLanes.includes(lane) ? LANE_COLOR[lane] : "#9ca3af",
              }}
            >
              {LANE_DISPLAY[lane]}
            </button>
          ))}
        </div>
      </div>

      <div className="flex gap-3 pb-2">
        {filteredColumns.map((col) => (
          <Card
            key={col.milestone}
            className={`${
              expandedLane === col.milestone ? "flex-[2] min-w-[320px]" : "flex-1 min-w-[180px]"
            }`}
          >
            <CardHeader
              className="p-3 pb-2 cursor-pointer select-none"
              onClick={() =>
                setExpandedLane(expandedLane === col.milestone ? null : col.milestone)
              }
            >
              <CardTitle className="text-[11px] font-semibold uppercase tracking-wide text-gray-500 flex justify-between items-center">
                <span>{LANE_DISPLAY[col.milestone] || col.milestone}</span>
                <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                  {col.permits.length}
                </Badge>
              </CardTitle>
            </CardHeader>

            {/* Closed sub-status tabs */}
            {col.milestone === "Closed" && Object.keys(closedSubStatuses).length > 0 && (
              <div className="px-2 pb-1">
                <div className="flex gap-0.5 border-b border-gray-100 mb-1">
                  {CLOSED_SUBS.map((sub) => {
                    const count = closedSubStatuses[sub] || 0;
                    if (count === 0) return null;
                    const isActive = closedTab === sub;
                    const shortName = sub.replace("Closed - ", "");
                    return (
                      <button
                        key={sub}
                        onClick={(e) => {
                          e.stopPropagation();
                          setClosedTab(isActive ? null : sub);
                        }}
                        className={`flex-1 text-[9px] py-1.5 px-1 text-center font-semibold uppercase tracking-wide transition-colors border-b-2 ${
                          isActive
                            ? "text-blue-600 border-blue-600 bg-blue-50"
                            : "text-gray-400 border-transparent hover:text-gray-600"
                        }`}
                      >
                        <span>{shortName}</span>
                        <span className="ml-0.5 text-[8px] opacity-70">({count})</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            <CardContent className="p-2 pt-0 max-h-[60vh] overflow-y-auto">
              {col.permits.length === 0 ? (
                <div className="text-xs text-gray-300 text-center py-4">Empty</div>
              ) : (
                col.permits.map((permit) => (
                  <div
                    key={permit.record_number}
                    className={`relative p-2.5 mb-2 rounded border bg-white cursor-pointer hover:shadow-md transition-all text-xs ${
                      permit.changed
                        ? permit.change_info?.is_backward
                          ? "bg-red-50 border-red-200"
                          : permit.change_info?.is_tracked_milestone
                          ? "bg-purple-50 border-purple-200"
                          : "bg-blue-50 border-blue-200"
                        : "border-gray-200"
                    }`}
                    onClick={() => handleShowTimeline(permit.record_number)}
                  >
                    {permit.changed && (
                      <span
                        className={`absolute top-2 right-2 w-1.5 h-1.5 rounded-full ${
                          permit.change_info?.is_backward
                            ? "bg-red-500"
                            : permit.change_info?.is_tracked_milestone
                            ? "bg-purple-500"
                            : "bg-blue-500"
                        }`}
                      />
                    )}
                    <div
                      className="font-medium text-gray-900 truncate pr-3"
                      title={permit.address}
                    >
                      {permit.address}
                    </div>
                    <div className="text-[10px] text-gray-400 font-mono mt-0.5">
                      {permit.record_number}
                    </div>
                    <div className="mt-1.5">
                      <Badge variant="outline" className="text-[9px] px-1 py-0">
                        {permit.current_status}
                      </Badge>
                    </div>
                    {permit.changed && permit.change_info && (
                      <div className="mt-1 text-[10px] text-gray-500">
                        {permit.change_info.from_status} → {permit.change_info.to_status}
                      </div>
                    )}
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      <Dialog open={!!dialogPermit} onOpenChange={() => setDialogPermit(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-sm">Permit Timeline</DialogTitle>
          </DialogHeader>
          <div className="text-xs text-gray-500">{dialogPermit}</div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
