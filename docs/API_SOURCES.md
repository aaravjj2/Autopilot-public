# API source of truth

| Concern | Primary | Notes |
|---------|---------|-------|
| Trading, arb, risk, WS | **APEX** `backend_api.py` `:8000` | Use `NEXT_PUBLIC_APEX_API_URL` |
| Marketplace copy-trading | `autopilot-local/backend` `:8001` | Optional; arb routes should call APEX |

Frontend: [`autopilot-local/frontend/lib/backend-urls.ts`](../autopilot-local/frontend/lib/backend-urls.ts).
