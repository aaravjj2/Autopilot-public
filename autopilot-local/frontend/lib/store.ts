import { create } from "zustand";
import type { Position, AccountSnapshot, OpportunityScore, TradeProposal, AuditEvent } from "./api";

interface AppState {
  // Account
  account: AccountSnapshot | null;
  setAccount: (account: AccountSnapshot) => void;

  // Positions
  positions: Position[];
  setPositions: (positions: Position[]) => void;
  closedPositions: Position[];
  setClosedPositions: (positions: Position[]) => void;

  // Opportunities
  opportunities: OpportunityScore[];
  setOpportunities: (opportunities: OpportunityScore[]) => void;

  // Proposals
  proposals: TradeProposal[];
  setProposals: (proposals: TradeProposal[]) => void;

  // Events/Audit
  events: AuditEvent[];
  setEvents: (events: AuditEvent[]) => void;

  // WebSocket State
  wsConnected: boolean;
  setWsConnected: (connected: boolean) => void;
  wsLastUpdate: string | null;
  setWsLastUpdate: (timestamp: string | null) => void;
  wsDataStale: boolean;
  setWsDataStale: (stale: boolean) => void;
  
  // Handle WebSocket message
  handleWsMessage: (data: any) => void;

  // UI State
  selectedSymbol: string | null;
  setSelectedSymbol: (symbol: string | null) => void;
  
  selectedTimeframe: string;
  setSelectedTimeframe: (timeframe: string) => void;
  
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (collapsed: boolean) => void;

  // Theme
  theme: "light" | "dark";
  setTheme: (theme: "light" | "dark") => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  // Account
  account: null,
  setAccount: (account) => set({ account }),

  // Positions
  positions: [],
  setPositions: (positions) => set({ positions }),
  closedPositions: [],
  setClosedPositions: (closedPositions) => set({ closedPositions }),

  // Opportunities
  opportunities: [],
  setOpportunities: (opportunities) => set({ opportunities }),

  // Proposals
  proposals: [],
  setProposals: (proposals) => set({ proposals }),

  // Events
  events: [],
  setEvents: (events) => set({ events }),

  // WebSocket State
  wsConnected: false,
  setWsConnected: (wsConnected) => set({ wsConnected }),
  wsLastUpdate: null,
  setWsLastUpdate: (wsLastUpdate) => set({ wsLastUpdate }),
  wsDataStale: false,
  setWsDataStale: (wsDataStale) => set({ wsDataStale }),
  
  // Handle WebSocket message
  handleWsMessage: (data) => {
    const { type, ...payload } = data;
    
    switch (type) {
      case 'initial_data':
      case 'snapshot':
        set({
          account: payload.account ?? get().account,
          positions: payload.positions || [],
          opportunities: payload.opportunities || [],
          proposals: payload.proposals || [],
          events: payload.events?.length ? payload.events : get().events,
          wsDataStale: payload._is_stale || false,
          wsLastUpdate: payload.timestamp || new Date().toISOString(),
        });
        break;
      case 'data_updated':
        set({
          wsLastUpdate: new Date().toISOString(),
          wsDataStale: false,
        });
        break;
      case 'heartbeat':
      case 'pong':
        set({ wsLastUpdate: payload.timestamp || new Date().toISOString() });
        break;
      case 'account_update':
        set({ account: payload });
        break;
      case 'positions_update':
        set({ positions: payload.positions || [] });
        break;
      case 'orders_update':
        // Orders updated - could trigger UI refresh
        break;
      case 'opportunities_update':
        set({ opportunities: payload.opportunities || [] });
        break;
      case 'events_update':
        set({ events: payload.events || [] });
        break;
      default:
        break;
    }
  },

  // UI State
  selectedSymbol: null,
  setSelectedSymbol: (selectedSymbol) => set({ selectedSymbol }),
  
  selectedTimeframe: "1D",
  setSelectedTimeframe: (selectedTimeframe) => set({ selectedTimeframe }),
  
  sidebarCollapsed: false,
  setSidebarCollapsed: (sidebarCollapsed) => set({ sidebarCollapsed }),

  // Theme
  theme: "dark",
  setTheme: (theme) => set({ theme }),
}));