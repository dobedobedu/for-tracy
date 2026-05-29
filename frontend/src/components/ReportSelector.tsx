import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Upload } from "@/api";

export function ReportSelector({
  uploads,
  fromDate,
  toDate,
  onSelect,
}: {
  uploads: Upload[];
  fromDate: string | null;
  toDate: string | null;
  onSelect: (from: string, to: string) => void;
}) {
  const [hoveredDate, setHoveredDate] = useState<string | null>(null);

  // Default calendar month to the latest upload date, not current month
  const latestDate = uploads.length > 0
    ? [...uploads].sort((a, b) => b.report_date.localeCompare(a.report_date))[0].report_date
    : null;
  const latestMonth = latestDate
    ? new Date(parseInt(latestDate.slice(0, 4)), parseInt(latestDate.slice(5, 7)) - 1, 1)
    : new Date();

  const [calendarMonth, setCalendarMonth] = useState<Date>(latestMonth);

  // When uploads change, reset calendar to latest month
  useEffect(() => {
    if (latestDate) {
      setCalendarMonth(new Date(parseInt(latestDate.slice(0, 4)), parseInt(latestDate.slice(5, 7)) - 1, 1));
    }
  }, [latestDate]);

  const sorted = [...uploads].sort((a, b) => b.report_date.localeCompare(a.report_date));
  const dates = new Set(uploads.map((u) => u.report_date));

  const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  const shiftMonth = (delta: number) => {
    setCalendarMonth((prev) => {
      const next = new Date(prev);
      next.setMonth(next.getMonth() + delta);
      return next;
    });
  };

  const renderCalendar = () => {
    const year = calendarMonth.getFullYear();
    const month = calendarMonth.getMonth();
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    const days: React.ReactNode[] = [];
    for (let i = 0; i < firstDay; i++) {
      days.push(<div key={`pad-${i}`} className="h-7 w-7" />);
    }

    for (let day = 1; day <= daysInMonth; day++) {
      const dateStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
      const hasUpload = dates.has(dateStr);
      const isSelected = fromDate === dateStr || toDate === dateStr;
      const isHovered = hoveredDate === dateStr;

      days.push(
        <button
          key={day}
          disabled={!hasUpload}
          onClick={() => {
            if (!fromDate || (fromDate && toDate)) {
              onSelect(dateStr, dateStr);
            } else if (dateStr < fromDate) {
              onSelect(dateStr, fromDate);
            } else {
              onSelect(fromDate, dateStr);
            }
          }}
          onMouseEnter={() => hasUpload && setHoveredDate(dateStr)}
          onMouseLeave={() => setHoveredDate(null)}
          className={`h-7 w-7 rounded text-xs flex items-center justify-center transition-colors ${
            isSelected
              ? "bg-blue-600 text-white"
              : isHovered
              ? "bg-blue-100 text-blue-700"
              : hasUpload
              ? "bg-blue-50 text-blue-700 hover:bg-blue-100"
              : "text-gray-300 cursor-default"
          }`}
        >
          {day}
        </button>
      );
    }

    return (
      <div>
        <div className="flex items-center justify-between mb-2">
          <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-xs" onClick={() => shiftMonth(-1)}>
            ◀
          </Button>
          <span className="text-sm font-semibold">
            {monthNames[month]} {year}
          </span>
          <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-xs" onClick={() => shiftMonth(1)}>
            ▶
          </Button>
        </div>
        <div className="grid grid-cols-7 gap-1">
          {["S", "M", "T", "W", "T", "F", "S"].map((d) => (
            <div key={d} className="h-7 w-7 text-center text-[10px] text-gray-400 font-medium">
              {d}
            </div>
          ))}
          {days}
        </div>
        <div className="mt-2 text-[10px] text-gray-400 flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full bg-blue-500" /> Upload day
          <span className="inline-block w-2 h-2 rounded bg-blue-600 ml-1" /> Selected
        </div>
      </div>
    );
  };

  return (
    <Card className="flex-1">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold">Select Reports to Compare</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex gap-10">
          {/* Calendar View */}
          <div className="flex-shrink-0 min-w-[260px]">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-3">
              Calendar View
            </h3>
            {renderCalendar()}
          </div>

          {/* List View */}
          <div className="flex-1 min-w-0">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-3">
              List View
            </h3>
            <div className="max-h-[260px] overflow-auto border rounded-md">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs">Date</TableHead>
                    <TableHead className="text-xs">Filename</TableHead>
                    <TableHead className="text-xs text-right">Permits</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sorted.map((u) => (
                    <TableRow
                      key={u.id}
                      className={`cursor-pointer ${
                        fromDate === u.report_date || toDate === u.report_date
                          ? "bg-blue-50"
                          : ""
                      }`}
                      onClick={() => {
                        if (!fromDate || (fromDate && toDate)) {
                          onSelect(u.report_date, u.report_date);
                        } else if (u.report_date < fromDate) {
                          onSelect(u.report_date, fromDate);
                        } else {
                          onSelect(fromDate, u.report_date);
                        }
                      }}
                    >
                      <TableCell className="text-xs font-medium whitespace-nowrap pr-4">{u.report_date}</TableCell>
                      <TableCell className="text-xs truncate max-w-[260px] pr-4">{u.filename}</TableCell>
                      <TableCell className="text-xs text-right whitespace-nowrap">{u.row_count_after_scope.toLocaleString()}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            <div className="text-xs text-gray-400 mt-3">
              {fromDate && toDate ? (
                <span>
                  Comparing <Badge variant="outline">{fromDate}</Badge> →{" "}
                  <Badge variant="outline">{toDate}</Badge>
                </span>
              ) : (
                "Click a date or row to select reports"
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
