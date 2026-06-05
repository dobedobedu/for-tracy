import { useState, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { getCommunities, type Community } from "@/api";

const PINNED_KEY = "fortracy_pinned_communities";
const HIDDEN_KEY = "fortracy_hidden_communities";
const DEFAULT_VISIBLE_COUNT = 5;

function loadSet(key: string): string[] {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveSet(key: string, values: string[]) {
  localStorage.setItem(key, JSON.stringify(values));
}

export function CommunityFilter({
  fromDate,
  toDate,
  selected,
  onToggle,
  onClear,
  onSelectAllLwr,
  lwrCommunityNames,
}: {
  fromDate?: string;
  toDate?: string;
  selected: string[];
  onToggle: (community: string) => void;
  onClear: () => void;
  onSelectAllLwr: () => void;
  lwrCommunityNames: string[];
}) {
  const [communities, setCommunities] = useState<Community[]>([]);
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [pinned, setPinned] = useState<string[]>(loadSet(PINNED_KEY));
  const [hidden, setHidden] = useState<string[]>(loadSet(HIDDEN_KEY));

  useEffect(() => {
    getCommunities(false, fromDate, toDate).then(setCommunities);
  }, [fromDate, toDate]);

  const isPinned = (name: string) => pinned.includes(name);
  const isHidden = (name: string) => hidden.includes(name);

  const unpin = (name: string) => {
    setPinned((prev) => {
      const next = prev.filter((n) => n !== name);
      saveSet(PINNED_KEY, next);
      return next;
    });
    setHidden((prev) => {
      const next = prev.includes(name) ? prev : [...prev, name];
      saveSet(HIDDEN_KEY, next);
      return next;
    });
  };

  const pin = (name: string) => {
    setPinned((prev) => {
      const next = prev.includes(name) ? prev : [...prev, name];
      saveSet(PINNED_KEY, next);
      return next;
    });
    setHidden((prev) => {
      const next = prev.filter((n) => n !== name);
      saveSet(HIDDEN_KEY, next);
      return next;
    });
  };

  const togglePin = (name: string) => {
    if (isPinned(name)) unpin(name);
    else pin(name);
  };

  const pinnedCommunities = communities.filter((c) => isPinned(c.name));
  const eligibleForDefault = communities.filter((c) => !isPinned(c.name) && !isHidden(c.name));
  const topDefaults = eligibleForDefault.slice(0, DEFAULT_VISIBLE_COUNT);
  const visibleCommunities = [...pinnedCommunities, ...topDefaults];
  const hiddenCount = communities.length - visibleCommunities.length;

  const searchResults = search
    ? communities.filter((c) => c.name.toLowerCase().includes(search.toLowerCase()))
    : [];

  // In the modal, show all communities sorted alphabetically, filtered by search
  const modalCommunities = [...communities]
    .filter((c) => !search || c.name.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => a.name.localeCompare(b.name));

  return (
    <div className="space-y-3">
      {/* Search bar */}
      <div className="flex items-center gap-3">
        <Input
          placeholder="Search communities..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-[280px] text-sm"
        />
        {selected.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {selected.map((name) => (
              <Badge
                key={name}
                variant="default"
                className="cursor-pointer text-xs"
                onClick={() => onToggle(name)}
              >
                {name} ×
              </Badge>
            ))}
          </div>
        )}
      </div>

      {/* Community chips row */}
      <div className="flex flex-wrap gap-2 items-center">
        {/* All badge */}
        <Badge
          variant={selected.length === 0 ? "default" : "outline"}
          className="cursor-pointer text-xs"
          onClick={onClear}
        >
          All
        </Badge>

        {/* All Lakewood Ranch button - uses regular <button> for reliable click handling */}
        <button
          type="button"
          data-testid="all-lakewood-ranch-chip"
          onClick={() => {
            onSelectAllLwr();
          }}
          title="Select all 13 Lakewood Ranch communities"
          className={`inline-flex items-center justify-center h-7 px-3 rounded-2xl border text-xs font-medium whitespace-nowrap transition-all cursor-pointer ${
            lwrCommunityNames.length > 0 &&
            lwrCommunityNames.every((c) => selected.includes(c)) &&
            selected.length === lwrCommunityNames.length
              ? "bg-primary text-primary-foreground border-transparent"
              : "border-border text-foreground hover:bg-muted"
          }`}
        >
          All Lakewood Ranch ({lwrCommunityNames.length})
        </button>

        {/* Visible community chips with pin handles */}
        {visibleCommunities.map((c) => (
          <Badge
            key={c.name}
            variant={selected.includes(c.name) ? "default" : "outline"}
            className="cursor-pointer text-xs inline-flex items-center gap-1"
            onClick={() => onToggle(c.name)}
          >
            <span
              onClick={(e) => {
                e.stopPropagation();
                togglePin(c.name);
              }}
              className={`select-none transition-colors ${
                isPinned(c.name) ? "text-blue-500" : "text-gray-300 hover:text-blue-400"
              }`}
              title={isPinned(c.name) ? "Unpin" : "Pin"}
            >
              ⋮⋮
            </span>
            {c.name} ({c.count})
          </Badge>
        ))}

        {/* Search results (not already visible) */}
        {search &&
          searchResults
            .filter((c) => !visibleCommunities.some((v) => v.name === c.name))
            .map((c) => (
              <Badge
                key={c.name}
                variant={selected.includes(c.name) ? "default" : "outline"}
                className="cursor-pointer text-xs inline-flex items-center gap-1"
                onClick={() => onToggle(c.name)}
              >
                <span
                  onClick={(e) => {
                    e.stopPropagation();
                    pin(c.name);
                  }}
                  className="select-none text-gray-300 hover:text-blue-400 transition-colors"
                  title="Pin"
                >
                  ⋮⋮
                </span>
                {c.name} ({c.count})
              </Badge>
            ))}

        {/* Show more button */}
        {!search && hiddenCount > 0 && (
          <button
            onClick={() => setModalOpen(true)}
            className="text-xs text-blue-600 hover:text-blue-800 font-medium py-1 px-2 rounded hover:bg-blue-50 transition-colors"
          >
            +{hiddenCount} more
          </button>
        )}
      </div>

      {/* All Communities Modal with tile grid */}
      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="text-sm flex justify-between items-center">
              <span>All Communities ({communities.length})</span>
              <span className="text-[10px] text-gray-400 font-normal">
                {pinned.length} pinned · {hidden.length} hidden
              </span>
            </DialogTitle>
          </DialogHeader>

          <div className="flex items-center gap-2 mb-3">
            <Input
              placeholder="Filter communities..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="text-sm flex-1"
            />
            <button
              onClick={() => {
                onSelectAllLwr();
                setModalOpen(false);
              }}
              className="text-xs px-3 py-2 rounded border border-blue-300 bg-blue-50 hover:bg-blue-100 text-blue-700 font-medium transition-colors whitespace-nowrap"
              title="Select all Lakewood Ranch communities and close"
            >
              All Lakewood Ranch
            </button>
            <button
              onClick={() => {
                onClear();
                setModalOpen(false);
              }}
              className="text-xs px-3 py-2 rounded border border-gray-300 hover:bg-gray-50 text-gray-600 font-medium transition-colors whitespace-nowrap"
              title="Clear all filters and close"
            >
              Clear
            </button>
          </div>

          <div className="overflow-y-auto flex-1 pr-1">
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
              {modalCommunities.map((c) => {
                const isSelected = selected.includes(c.name);
                const pinnedHere = isPinned(c.name);
                return (
                  <button
                    key={c.name}
                    onClick={() => onToggle(c.name)}
                    className={`relative text-left rounded-md border px-3 py-2.5 text-xs transition-all min-h-[58px] ${
                      isSelected
                        ? "bg-blue-50 border-blue-400 text-blue-800 ring-1 ring-blue-300"
                        : "bg-white border-gray-200 hover:border-blue-300 hover:bg-blue-50/50 text-gray-700"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-1">
                      <span className="font-medium leading-tight line-clamp-2 break-words">
                        {c.name}
                      </span>
                      <span
                        onClick={(e) => {
                          e.stopPropagation();
                          togglePin(c.name);
                        }}
                        className={`select-none cursor-pointer flex-shrink-0 transition-colors ${
                          pinnedHere ? "text-blue-500" : "text-gray-300 hover:text-blue-400"
                        }`}
                        title={pinnedHere ? "Unpin" : "Pin"}
                      >
                        ⋮⋮
                      </span>
                    </div>
                    <div className="flex items-center justify-between mt-1">
                      <span className="text-[10px] text-gray-400">{c.count} permits</span>
                      {isSelected && (
                        <span className="text-blue-600 font-bold text-sm leading-none">✓</span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
            {modalCommunities.length === 0 && (
              <div className="text-center text-xs text-gray-400 py-8">
                No communities match "{search}"
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
