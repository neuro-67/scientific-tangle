import type { QueryFilters } from "../model/query.types";

const STORAGE_KEY = "scientific-tangle-history";

export type QueryHistoryItem = {
  id: string;
  question: string;
  filters: QueryFilters;
  createdAt: string;
  favorite: boolean;
};

function readStorage(): QueryHistoryItem[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as QueryHistoryItem[]) : [];
  } catch {
    return [];
  }
}

function writeStorage(items: QueryHistoryItem[]) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
}

export function getQueryHistory(): QueryHistoryItem[] {
  return readStorage();
}

export function addQueryHistory(
  question: string,
  filters: QueryFilters,
  favorite = false
) {
  const items = readStorage();
  const existingIndex = items.findIndex((i) => i.question === question);
  if (existingIndex >= 0) {
    const [existing] = items.splice(existingIndex, 1);
    existing.createdAt = new Date().toISOString();
    if (favorite) existing.favorite = true;
    items.unshift(existing);
    writeStorage(items);
    return existing;
  }
  const item: QueryHistoryItem = {
    id: crypto.randomUUID(),
    question,
    filters,
    createdAt: new Date().toISOString(),
    favorite,
  };
  items.unshift(item);
  writeStorage(items);
  return item;
}

export function toggleQueryHistoryFavorite(id: string) {
  const items = readStorage();
  const item = items.find((i) => i.id === id);
  if (item) {
    item.favorite = !item.favorite;
    writeStorage(items);
  }
  return item;
}

export function removeQueryHistory(id: string) {
  const items = readStorage().filter((i) => i.id !== id);
  writeStorage(items);
}
