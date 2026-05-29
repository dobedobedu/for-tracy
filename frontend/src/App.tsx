import { useState, useEffect, useCallback } from "react";
import { UploadZone } from "@/components/UploadZone";
import { ReportSelector } from "@/components/ReportSelector";
import { TransitionSummary } from "@/components/TransitionSummary";
import { CommunityFilter } from "@/components/CommunityFilter";
import { KanbanBoard } from "@/components/KanbanBoard";
import { getUploads, getCompare, getKanban, type Upload, type CompareResult } from "@/api";

export default function App() {
  const [uploads, setUploads] = useState<Upload[]>([]);
  const [fromDate, setFromDate] = useState<string | null>(null);
  const [toDate, setToDate] = useState<string | null>(null);
  const [compareResult, setCompareResult] = useState<CompareResult | null>(null);
  const [selectedTransition, setSelectedTransition] = useState<{ from: string; to: string } | null>(null);
  const [selectedCommunities, setSelectedCommunities] = useState<string[]>([]);
  const [legendFilter, setLegendFilter] = useState<"changed" | "tracked" | "backward" | null>(null);
  const [kanbanData, setKanbanData] = useState<any>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = useCallback(() => setRefreshKey((k) => k + 1), []);

  useEffect(() => {
    getUploads().then(setUploads);
  }, [refreshKey]);

  useEffect(() => {
    if (uploads.length >= 2) {
      const sorted = [...uploads].sort((a, b) => b.report_date.localeCompare(a.report_date));
      setToDate(sorted[0].report_date);
      setFromDate(sorted[1].report_date);
    }
  }, [uploads]);

  useEffect(() => {
    if (fromDate && toDate) {
      getCompare(fromDate, toDate).then(setCompareResult);
    }
  }, [fromDate, toDate]);

  useEffect(() => {
    getKanban(selectedCommunities.length > 0 ? selectedCommunities : undefined, toDate || undefined).then(setKanbanData);
  }, [selectedCommunities, toDate, refreshKey]);

  const handleUpload = () => {
    refresh();
  };

  const handleSelectReports = (from: string, to: string) => {
    setFromDate(from);
    setToDate(to);
    setSelectedTransition(null);
  };

  const handleSelectTransition = (from: string, to: string) => {
    // Deselect when empty strings are passed (toggle off)
    if (!from && !to) {
      setSelectedTransition(null);
    } else {
      setSelectedTransition({ from, to });
    }
  };

  const handleToggleCommunity = (community: string) => {
    setSelectedCommunities((prev) =>
      prev.includes(community) ? prev.filter((c) => c !== community) : [...prev, community]
    );
  };

  const handleLegendFilter = (filter: "changed" | "tracked" | "backward" | null) => {
    setLegendFilter((prev) => (prev === filter ? null : filter));
  };

  return (
    <div className="min-h-screen bg-[#f8f9fb]">
      <header className="bg-[#0c111d] text-white px-6 py-4 flex items-center justify-between">
        <div className="flex items-baseline gap-3">
          <h1 className="text-lg font-bold tracking-tight">For Tracy</h1>
          <span className="text-xs opacity-50 font-normal">Lakewood Ranch Permit Tracker</span>
        </div>
      </header>

      <main className="max-w-[1480px] mx-auto p-6 space-y-8">
        {/* Upload + Report Selection */}
        <div className="flex gap-4 items-stretch">
          <UploadZone onUpload={handleUpload} />
          <ReportSelector
            uploads={uploads}
            fromDate={fromDate}
            toDate={toDate}
            onSelect={handleSelectReports}
          />
        </div>

        {/* Transition Summary */}
        {compareResult && compareResult.summary.length > 0 && (
          <TransitionSummary
            summary={compareResult.summary}
            selected={selectedTransition}
            onSelect={handleSelectTransition}
          />
        )}

        {/* Community Filter */}
        {uploads.length > 0 && (
          <section className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                Communities
              </h2>
              {selectedCommunities.length > 0 && (
                <button
                  onClick={() => setSelectedCommunities([])}
                  className="text-[10px] text-gray-400 hover:text-gray-600 underline underline-offset-2 transition-colors"
                >
                  Clear all ({selectedCommunities.length})
                </button>
              )}
            </div>
            <CommunityFilter
              fromDate={fromDate || undefined}
              toDate={toDate || undefined}
              selected={selectedCommunities}
              onToggle={handleToggleCommunity}
              onClear={() => setSelectedCommunities([])}
            />
          </section>
        )}

        {/* Subtle divider */}
        <div className="h-px bg-gray-200/60" />

        {/* Kanban Board */}
        {kanbanData && (
          <KanbanBoard
            data={kanbanData}
            selectedTransition={selectedTransition}
            legendFilter={legendFilter}
            onLegendFilter={handleLegendFilter}
          />
        )}
      </main>
    </div>
  );
}
