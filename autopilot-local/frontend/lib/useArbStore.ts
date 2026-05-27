import { create } from "zustand";
import { applyPatch, type Operation } from "fast-json-patch";
import type { ArbOpportunity } from "@/types/arb";
import { normalizeArbRows } from "@/lib/arbNormalize";

type ArbDocument = { opportunities: ArbOpportunity[] };

interface ArbState {
  opportunities: ArbOpportunity[];
  streamConnected: boolean;
  lastPatchAt: number | null;
  patchMode: boolean;
  maxEdge: number;
  setConnected: (v: boolean) => void;
  setStatus: (maxEdge: number, patchMode?: boolean) => void;
  applySync: (rows: ArbOpportunity[]) => void;
  applyPatches: (patches: Operation[]) => void;
  handleStreamMessage: (msg: Record<string, unknown>) => void;
}

export const useArbStore = create<ArbState>((set, get) => ({
  opportunities: [],
  streamConnected: false,
  lastPatchAt: null,
  patchMode: true,
  maxEdge: 0,

  setConnected: (streamConnected) => set({ streamConnected }),

  setStatus: (maxEdge, patchMode) =>
    set({
      maxEdge,
      ...(patchMode !== undefined ? { patchMode } : {}),
    }),

  applySync: (rows) =>
    set({
      opportunities: [...rows].sort((a, b) => b.net_edge - a.net_edge),
      lastPatchAt: Date.now(),
    }),

  applyPatches: (patches) => {
    try {
      const doc: ArbDocument = { opportunities: get().opportunities };
      const next = applyPatch(doc, patches, true, false).newDocument;
      set({
        opportunities: [...next.opportunities].sort((a, b) => b.net_edge - a.net_edge),
        lastPatchAt: Date.now(),
      });
    } catch (err) {
      console.warn("arb patch apply failed", err);
    }
  },

  handleStreamMessage: (msg) => {
    const type = msg.type as string;
    if (type === "heartbeat") {
      return;
    }
    if (type === "sync" || type === "data") {
      const raw = (msg.opportunities as unknown[]) ?? [];
      get().applySync(normalizeArbRows(raw));
      return;
    }
    if (type === "patch" && Array.isArray(msg.patches)) {
      get().applyPatches(msg.patches as Operation[]);
      return;
    }
    if (type === "status") {
      get().setStatus(
        Number(msg.max_edge ?? 0),
        Boolean(msg.patch_mode ?? get().patchMode)
      );
    }
  },
}));
