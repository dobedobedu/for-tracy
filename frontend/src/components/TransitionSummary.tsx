import { Badge } from "@/components/ui/badge";

export function TransitionSummary({
  summary,
  selected,
  onSelect,
}: {
  summary: { from: string; to: string; count: number }[];
  selected: { from: string; to: string } | null;
  onSelect: (from: string, to: string) => void;
}) {
  if (summary.length === 0) return null;

  return (
    <div className="flex items-center gap-2 text-sm py-2 px-4 bg-white rounded-lg border">
      <span className="text-gray-500 text-xs uppercase tracking-wide font-medium">
        Changes:
      </span>
      {summary.map((item) => (
        <button
          key={`${item.from}-${item.to}`}
          onClick={() =>
            onSelect(
              selected?.from === item.from && selected?.to === item.to ? "" : item.from,
              selected?.from === item.from && selected?.to === item.to ? "" : item.to
            )
          }
          className="flex items-center gap-1.5"
        >
          <span className="text-gray-600 text-xs">
            {item.from} → {item.to}
          </span>
          <Badge
            variant={
              selected?.from === item.from && selected?.to === item.to
                ? "default"
                : "secondary"
            }
            className="cursor-pointer text-xs px-2 py-0.5"
          >
            {item.count}
          </Badge>
        </button>
      ))}
    </div>
  );
}
