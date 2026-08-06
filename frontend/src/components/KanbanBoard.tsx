import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { getTimeline } from "@/api";

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
    is_new?: boolean;
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
  legendFilter: "changed" | "new" | "backward" | null;
  onLegendFilter: (filter: "changed" | "new" | "backward" | null) => void;
}) {
  const [dialogPermit, setDialogPermit] = useState<string | null>(null);
  const [timelineData, setTimelineData] = useState<any | null>(null);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [visibleLanes, setVisibleLanes] = useState<string[]>(DEFAULT_VISIBLE_LANES);
  const [expandedLane, setExpandedLane] = useState<string | null>(null);
  const [showLaneEditor, setShowLaneEditor] = useState(false);
  const [closedTab, setClosedTab] = useState<string | null>(null);

  const columns = data.columns || [];
  const closedSubStatuses = data.closed_sub_statuses || {};

  useEffect(() => {
    if (dialogPermit) {
      setTimelineLoading(true);
      getTimeline(dialogPermit)
        .then((data) => {
          setTimelineData(data);
          setTimelineLoading(false);
        })
        .catch((err) => {
          console.error("Failed to fetch timeline:", err);
          setTimelineLoading(false);
        });
    } else {
      setTimelineData(null);
    }
  }, [dialogPermit]);

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

  const isPermitMatchingFilter = (p: Permit, filter: "changed" | "new" | "backward" | null) => {
    if (!filter) return true;
    if (!p.changed || !p.change_info) return false;
    if (filter === "backward") return p.change_info.is_backward;
    if (filter === "new") return p.change_info.is_new || p.change_info.from_status === "New Application";
    if (filter === "changed") return !p.change_info.is_backward;
    return false;
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

      const matchingCount = permits.filter((p) => isPermitMatchingFilter(p, legendFilter)).length;

      return { ...col, permits, matchingCount };
    });

  const legendItems: { key: "changed" | "new" | "backward"; label: string; dotClass: string }[] = [
    { key: "changed", label: "Changed", dotClass: "bg-blue-500" },
    { key: "new", label: "New Permit", dotClass: "bg-emerald-500" },
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
        {filteredColumns.map((col) => {
          const isExpanded = expandedLane === col.milestone;
          return (
            <Card
              key={col.milestone}
              className={`${
                isExpanded ? "flex-[3.5] min-w-[420px]" : "flex-1 min-w-[180px]"
              } transition-all duration-300`}
            >
              <CardHeader
                className={`${isExpanded ? "p-4 pb-3" : "p-3 pb-2"} cursor-pointer select-none`}
                onClick={() =>
                  setExpandedLane(isExpanded ? null : col.milestone)
                }
              >
                <CardTitle className={`${isExpanded ? "text-sm font-bold" : "text-[11px] font-semibold"} uppercase tracking-wide text-gray-500 flex justify-between items-center`}>
                  <span>{LANE_DISPLAY[col.milestone] || col.milestone}</span>
                  <Badge variant="secondary" className={`${isExpanded ? "text-xs px-2 py-0.5" : "text-[10px] px-1.5 py-0"}`}>
                    {legendFilter ? `${col.matchingCount} / ${col.permits.length}` : col.permits.length}
                  </Badge>
                </CardTitle>
              </CardHeader>

              {/* Closed sub-status tabs */}
              {col.milestone === "Closed" && Object.keys(closedSubStatuses).length > 0 && (
                <div className={`${isExpanded ? "px-4 pb-2" : "px-2 pb-1"}`}>
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
                          className={`flex-1 text-center font-semibold uppercase tracking-wide transition-colors border-b-2 ${
                            isExpanded ? "text-[11px] py-2 px-2" : "text-[9px] py-1.5 px-1"
                          } ${
                            isActive
                              ? "text-blue-600 border-blue-600 bg-blue-50"
                              : "text-gray-400 border-transparent hover:text-gray-600"
                          }`}
                        >
                          <span>{shortName}</span>
                          <span className={`ml-0.5 opacity-70 ${isExpanded ? "text-[10px]" : "text-[8px]"}`}>({count})</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              <CardContent className={`${isExpanded ? "p-4 pt-0" : "p-2 pt-0"} max-h-[60vh] overflow-y-auto`}>
                {col.permits.length === 0 ? (
                  <div className={`${isExpanded ? "text-sm" : "text-xs"} text-gray-300 text-center py-4`}>Empty</div>
                ) : (
                  col.permits.map((permit) => {
                    const isMatch = isPermitMatchingFilter(permit, legendFilter);
                    const isDimmed = legendFilter !== null && !isMatch;
                    return (
                      <div
                        key={permit.record_number}
                        className={`relative mb-2 rounded border bg-white cursor-pointer transition-all ${
                          isExpanded ? "p-4 text-sm" : "p-2.5 text-xs"
                        } ${
                          isDimmed
                            ? "opacity-35 grayscale-[30%] border-gray-200 hover:opacity-80"
                            : permit.changed
                            ? permit.change_info?.is_new || permit.change_info?.from_status === "New Application"
                              ? "bg-emerald-50 border-emerald-200 hover:shadow-md"
                              : permit.change_info?.is_backward
                              ? "bg-red-50 border-red-200 hover:shadow-md"
                              : "bg-blue-50 border-blue-200 hover:shadow-md"
                            : "border-gray-200 hover:shadow-md"
                        }`}
                        onClick={() => handleShowTimeline(permit.record_number)}
                      >
                      {permit.changed && (
                        <span
                          className={`absolute rounded-full ${
                            isExpanded ? "top-4 right-4 w-2.5 h-2.5" : "top-2 right-2 w-1.5 h-1.5"
                          } ${
                            permit.change_info?.is_new || permit.change_info?.from_status === "New Application"
                              ? "bg-emerald-500"
                              : permit.change_info?.is_backward
                              ? "bg-red-500"
                              : "bg-blue-500"
                          }`}
                        />
                      )}
                      <div
                        className={`font-semibold text-gray-900 truncate pr-3 ${
                          isExpanded ? "text-sm md:text-base leading-snug" : "text-xs font-medium"
                        }`}
                        title={permit.address}
                      >
                        {permit.address}
                      </div>
                      <div className={`text-gray-400 font-mono mt-0.5 ${
                        isExpanded ? "text-xs" : "text-[10px]"
                      }`}>
                        {permit.record_number}
                      </div>
                      <div className="mt-1.5 flex items-center gap-1.5 flex-wrap">
                        <Badge variant="outline" className={`${isExpanded ? "text-xs px-2 py-0.5" : "text-[9px] px-1 py-0"}`}>
                          {permit.current_status}
                        </Badge>
                        {(permit.change_info?.is_new || permit.change_info?.from_status === "New Application") && (
                          <Badge className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-[9px] px-1.5 py-0 border-0">
                            NEW
                          </Badge>
                        )}
                      </div>
                      {permit.changed && permit.change_info && (
                        <div className={`mt-1.5 text-gray-600 ${
                          isExpanded ? "text-xs" : "text-[10px]"
                        }`}>
                          {permit.change_info.from_status} → {permit.change_info.to_status}
                        </div>
                      )}
                    </div>
                  );
                })
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      <Dialog open={!!dialogPermit} onOpenChange={() => setDialogPermit(null)}>
        <DialogContent className="max-w-md md:max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-base font-semibold">Permit Details & Timeline</DialogTitle>
          </DialogHeader>
          {timelineLoading && (
            <div className="flex justify-center items-center py-8 text-sm text-gray-500">
              <span className="animate-pulse">Loading timeline data...</span>
            </div>
          )}
          {!timelineLoading && timelineData && (
            <div className="space-y-5">
              {/* Permit Summary Card */}
              <div className="p-4 bg-gray-50 border rounded-lg space-y-2">
                <div className="flex justify-between items-start gap-4">
                  <div>
                    <h3 className="font-bold text-gray-900 text-sm md:text-base leading-snug">{timelineData.permit.address}</h3>
                    <p className="text-xs text-gray-400 font-mono mt-0.5">{timelineData.permit.record_number}</p>
                  </div>
                  <Badge 
                    style={{
                      backgroundColor: `${LANE_COLOR[timelineData.permit.current_milestone] || '#9ca3af'}15`,
                      color: LANE_COLOR[timelineData.permit.current_milestone] || '#9ca3af',
                      borderColor: `${LANE_COLOR[timelineData.permit.current_milestone] || '#9ca3af'}40`
                    }}
                    variant="outline" 
                    className="text-xs font-semibold px-2 py-0.5 border"
                  >
                    {timelineData.permit.current_status}
                  </Badge>
                </div>
                {timelineData.permit.description && (
                  <p className="text-xs text-gray-500 italic line-clamp-2 mt-1">{timelineData.permit.description}</p>
                )}
                <div className="h-px bg-gray-200 my-2" />
                <div className="grid grid-cols-2 gap-2 text-[11px] text-gray-500">
                  <div>
                    <span className="font-medium text-gray-400">First Applied:</span>{" "}
                    <span className="font-semibold text-gray-700">{timelineData.permit.first_seen_date}</span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-400">Last Seen:</span>{" "}
                    <span className="font-semibold text-gray-700">{timelineData.permit.last_seen_date}</span>
                  </div>
                </div>
              </div>

              {/* Timeline Chronology */}
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-3">History / Observations</h4>
                <div className="relative pl-6 space-y-4 border-l border-gray-200 ml-3">
                  {timelineData.timeline.map((entry: any, index: number) => {
                    const milestoneColor = LANE_COLOR[entry.milestone] || "#9ca3af";
                    return (
                      <div key={index} className="relative">
                        {/* Dot on the timeline line */}
                        <span 
                          style={{ backgroundColor: milestoneColor }}
                          className={`absolute -left-[30px] top-1 rounded-full border-4 border-white ${
                            entry.is_status_change ? 'w-4 h-4 -left-[32px]' : 'w-3 h-3'
                          }`}
                        />
                        <div className="space-y-0.5">
                          <div className="flex items-center gap-2">
                            <span className="text-[11px] font-mono text-gray-400">{entry.observed_date}</span>
                            {entry.is_status_change && (
                              <Badge variant="secondary" className="text-[9px] px-1 py-0 bg-blue-50 text-blue-600 hover:bg-blue-50 border-none font-medium">
                                Status Change
                              </Badge>
                            )}
                          </div>
                          <div className="text-xs font-semibold text-gray-800">
                            {entry.status}
                          </div>
                          <div className="text-[10px] text-gray-400">
                            Milestone: {LANE_DISPLAY[entry.milestone] || entry.milestone} (Upload ID: {entry.upload_id})
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
