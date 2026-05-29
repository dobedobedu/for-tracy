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
}: {
  fromDate?: string;
  toDate?: string;
  selected: string[];
  onToggle: (community: string) => void;
  onClear: () => void;
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

      {/* All Communities Modal with pin/unpin */}
      <Dialog open={modalOpen} onOpenChange={setModalOpen}>
        <DialogContent className="max-w-lg max-h-[70vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="text-sm flex justify-between items-center">
              <span>All Communities ({communities.length})</span>
              <span className="text-[10px] text-gray-400 font-normal">
                {pinned.length} pinned · {hidden.length} hidden
              </span>
            </DialogTitle>
          </DialogHeader>

          <Input
            placeholder="Filter communities..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="text-sm mb-3"
          />

          <div className="overflow-y-auto flex-1 pr-1">
            <div className="grid grid-cols-1 gap-0.5">
              {[...communities]
                .filter((c) => !search || c.name.toLowerCase().includes(search.toLowerCase()))
                .sort((a, b) => a.name.localeCompare(b.name))
                .map((c) => (
                  <div
                    key={c.name}
                    className={`flex items-center justify-between px-3 py-2 rounded text-xs transition-colors ${
                      selected.includes(c.name)
                        ? "bg-blue-50 text-blue-700"
                        : "hover:bg-gray-50 text-gray-700"
                    }`}
                  >
                    <button
                      className="flex-1 text-left font-medium inline-flex items-center gap-1.5"
                      onClick={() => onToggle(c.name)}
                    >
                      <span
                        onClick={(e) => {
                          e.stopPropagation();
                          togglePin(c.name);
                        }}
                        className={`select-none transition-colors cursor-pointer ${
                          isPinned(c.name) ? "text-blue-500" : "text-gray-300 hover:text-blue-400"
                        }`}
                        title={isPinned(c.name) ? "Unpin" : "Pin"}
                      >
                        ⋮⋮
                      </span>
                      {c.name}
                      <span className="text-gray-400 font-normal">{c.count}</span>
                      {selected.includes(c.name) && (
                        <span className="ml-auto text-blue-600 font-bold">✓</span>
                      )}
                    </button>
                  </div>
                ))}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
