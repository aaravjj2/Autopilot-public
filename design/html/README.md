# APEX Terminal — HTML UI Designs (v2)

High-fidelity **static HTML prototypes** for the upgraded APEX trading terminal. Use these as the visual spec before porting to Next.js (`autopilot-local/frontend`).

## Open locally

```bash
cd design/html
# Any static server, or open files directly:
python3 -m http.server 5500
# → http://localhost:5500/index.html
```

## Pages

| File | Description |
|------|-------------|
| `index.html` | Marketing landing + feature map |
| `dashboard.html` | **Flagship** — KPIs, charts, watchlist, heatmap, pipeline, order ticket, ⌘K palette |
| `trading.html` | Multi-TF chart, options chain, greeks tab, blotter |
| `positions.html` | Open/closed book, close actions |
| `autopilot.html` | L0–L4 pipeline, proposals, risk gates |
| `signals.html` | Scored opportunities table + filters |
| `analytics.html` | Performance + arb backtest + category stats |
| `arb-radar.html` | Kalshi/Poly arb table, thesis panel, paper trade |
| `live-feed.html` | Audit event stream |
| `settings.html` | Live integration matrix + risk config |

## Design system

- `css/apex-terminal.css` — tokens, layout shell, components
- `js/terminal.js` — command palette (⌘K), tabs

## Figma import

In Figma MCP (Cursor): use **generate_figma_design** with:

- `outputMode`: `newFile` or `clipboard`
- Capture URL: `http://localhost:5500/dashboard.html` (with static server running)

Or paste HTML via Figma’s HTML-to-design plugins using these files.

## New vs current Next.js UI

- Dense **3-column shell** (nav + main + right inspector)
- **Command palette**, watchlist, sector heatmap, risk gauges
- **Order ticket** + alerts on every trade view
- **Arb thesis** side panel
- **Integration health** table with live detail strings
- IBM Plex typography, institutional dark palette
