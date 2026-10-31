# Stock Market Watch

Stock Market Watch is a Persian, right-to-left dashboard for analysing the Iranian stock market. The current application uses options data to estimate market expectations for underlying stocks and includes a separate stock catalogue that can be expanded with additional indicators over time.

## Current interface

The dashboard has five main tabs:

- **Stocks**, the default first tab, reads immediately from SQLite and refreshes company, industry, and market-value data from TSETMC in the background.
- **Watchlist** stores a persistent user-selected subset of symbols.
- **Strategy** applies enabled screening rules to current or archived rows.
- **Options** presents option-based market-expectation analysis.
- **Markets** presents six intraday Tehran-market charts today and is structured to expand with currency, gold, silver, copper, and other cross-market data.

The former Market and Bull Spread views are no longer shown in the interface. Their data retrieval, processing logic, and endpoints remain in the project for future use.

## Features

### Options

- Retrieves live Market Watch and best-order data from TSETMC.
- Detects option symbols and maps them to their underlying stocks.
- Calculates break-even distance, weighted averages, and effective returns.
- Shows the nearest expiries for every underlying symbol.
- Ranks options by their share of traded value.
- Supports symbol search, expiry-day filters, sorting, and calculation details.
- Keeps the last successful dataset visible during refresh and replaces it only after a new response is ready.
- Refreshes market-expectation data automatically.

### Stocks

- Retrieves official company and industry data from TSETMC for the configured symbols.
- Calculates market value from the latest closing price and listed shares, or issued ETF units for funds.
- Shows the latest traded price and closing price, with each price's percentage change from the previous close displayed underneath.
- Includes trading value and volume, listed-share count, free-float percentage, monthly average volume, and individual/institutional buy and sell volumes and participant counts.
- Reapplies configured manual free-float percentages for instruments whose TSETMC metadata omits that value, so online refreshes cannot clear the supplied figures.
- Keeps free float blank for `اهرم`, `توان`, `موج`, and `جوانه کوچک`, displaying a dash and skipping free-float-turnover calculation for those instruments.
- Derives free-float turnover, real-money flow, money-flow quality (real-money flow divided by trading value), price power (last trade versus closing price), real buy/sell per-capita values, and real buy power from the stored TSETMC fields. Trading value and real-money flow can be viewed in thousand US dollars using the latest dollar quote already received by the Markets tab.
- Calculates separate buy-side and sell-side value, volume, and order-count totals across the first five order-book levels for every symbol.
- Stores the latest complete catalogue in `data/stocks.db` and serves it immediately on page load.
- Replaces the SQLite rows atomically only after a background refresh is ready, so the table never disappears while online data is loading.
- Archives one complete row per symbol and trading day in SQLite. Standard symbols keep the first valid update received at or after 12:30 Tehran time; `عیار`, `طلا`, `کهربا`, `مثقال`, `نقرابی`, and `نقران` keep the first valid update received at or after their 18:00 close.
- Verifies the TSETMC market date before archiving, so a stale previous-session response is not recorded as a new day.
- Provides a manual refresh button without clearing the currently displayed table.
- Provides normal and industry-grouped views.
- Provides separate searches for symbol/company and industry.
- Sorts every column using a three-state cycle: ascending, descending, then the default market-value order.
- Filters rows by a minimum and/or maximum market value.
- Displays market value as a whole number in **HEMAT** (trillion tomans), with the unit shown in the column heading.
- Scales share and volume figures to fixed million/billion units shown on a second header line while retaining the exact value as a tooltip.
- Links every stock symbol directly to its official TSETMC instrument page.
- Supports horizontal table scrolling with the scrollbar, touch gestures, or mouse drag.
- Keeps the stock-table header visible inside a height-limited, vertically scrollable table area.
- Lets users hide or restore columns; the selection is saved in browser storage.
- Includes a persistent watchlist tab where symbols can be added directly from the Stocks table or removed from the Watchlist. Watchlist rows are stored in SQLite, reuse the full stock-column set, and remain available after a page refresh.
- Includes a Strategy tab that combines enabled filters with AND logic. Current trading value, free-float turnover, and real buy power can be compared with fixed thresholds and/or N-day averages; real-money flow supports positive-day streaks and comparison with its N-day average, while money-flow quality supports a fixed percentage comparison. Daily averages use SQLite snapshots, report partial history, and exclude zero or missing values.
- Adds configurable RSI, EMA, and MACD strategy rules based on archived daily closing prices. RSI supports a custom period, single threshold, or inclusive lower/upper range. EMA can compare the closing price with one EMA or detect a real upward/downward crossover between custom short and long periods. MACD supports custom fast, slow, and signal periods plus Signal/zero-line comparisons. Symbols with insufficient history are excluded with a coverage warning.
- Adds an independent latest-saved-data switch to the Stocks, Watchlist, and Strategy tabs. Each symbol uses its own newest daily SQLite snapshot, so the previous close remains available before the next market session populates live values.
- Archives refreshed watchlist symbols under the same 12:30/18:00 session rules, including symbols that are not part of the main stock catalogue.
- Stores persistent symbol notes in SQLite. Notes support importance levels from 1 to 5, editing, deletion, per-symbol history, and an all-symbol overview grouped by symbol.
- Uses a responsive glass-style interface with Persian typography and right-to-left controls.

### Markets

- Shows a compact cross-market overview above the charts: US dollar, NIMA negotiated-market dollar, 18-karat gold, global gold and silver ounces, global copper per metric ton, silver-bullion and copper-cathode certificates, plus IME rebar, zinc-ingot, and iron-ore-pellet certificate prices.
- Prefers Rahavard365's live last-trade WebSocket feed for listed prices. The US-dollar card never falls back to Rahavard's stale historical trade row; other assets may use their current `last_trade` response when no broadcast quote is available.
- Shows the latest net real-money flow for all gold funds, all silver funds, exchange-listed fixed-income funds, and the stock market. Fixed-income flow uses its direct TSETMC group row; dedicated fund groups are omitted from the scrollable industry panel to avoid duplication.
- Adds the full-day Tehran-market share and rights trading value as an
  overview card, excluding fixed-income, gold, silver, and all other funds.
- Reads Rahavard365 asset and commodity-fund data through the Flask backend, and uses Yahoo Finance for the global copper futures quote.
- Retrieves public intraday market series from TradersArena through the Flask backend.
- Shows six responsive SVG charts covering buy/sell order value, last-trade price distribution, stock money flow, positive/negative breadth, current order and queue value, and market excitement. The order chart includes the buy-to-sell percentage, while price-distribution bars show both count and share plus aggregate positive/negative percentages.
- Stores one updatable SQLite snapshot per Tehran day containing the latest free-dollar quote, share-only market trading value, all overview money flows, and every non-gold/non-silver industry money flow.
- Limits line charts to the regular 09:00–12:30 Tehran stock-market session.
- Supports on-demand refresh while preserving the previous in-memory dataset if a live refresh fails.
- Automatically refreshes the Stocks, Watchlist, Options, and Markets datasets every two minutes in the background, regardless of the active tab.

## Data endpoints

| Endpoint | Purpose |
|---|---|
| `/market-expectations` | Option-based market-expectation analysis |
| `/option-bases` | Underlying-symbol discovery and option-root mapping |
| `/stocks` | SQLite-backed online stock catalogue and trading indicators; use `use_saved_data=1` for each symbol's latest daily snapshot |
| `/stocks/history` | Latest archived daily stock rows; accepts optional `date=YYYY-MM-DD` and `symbol=...` filters |
| `/stock-watchlist` | Persistent watchlist collection: `GET` reads rows, `POST` adds a symbol, `GET ?refresh=1` refreshes live data, and `GET ?use_saved_data=1` reads latest snapshots |
| `/stock-watchlist/<symbol>` | Removes a watchlist symbol with `DELETE` |
| `/stock-notes` | Reads all notes or one symbol's notes with `GET`; creates a persistent note with `POST` |
| `/stock-notes/<id>` | Updates a note with `PUT` or removes it with `DELETE` |
| `/stock-strategy` | Evaluates enabled stock-strategy rules against current or latest saved rows and archived daily averages |
| `/watch-market` | Cross-market price/money-flow overview plus six intraday Markets-tab charts; use `refresh=1` to force a live refresh |
| `/watch-market/history` | Newest saved daily cross-market snapshots; accepts an optional `limit` |
| `/data` | Preserved data service for the former Market view |
| `/spread-data` | Preserved Bull Call Spread data and calculations |

Local snapshots are stored in:

- `data/trade_value_snapshot.json`
- `data/order_book_snapshot.json`

The latest stock catalogue, the daily `stock_daily_snapshots` archive, and the
daily `market_daily_snapshots` archive are stored in `data/stocks.db`. Each
archived stock row includes Gregorian and Jalali trade dates, the capture time,
session type, and the complete stock-row payload. Market snapshots keep the
latest value received during each Tehran calendar day.
The browser requests a stock refresh every two minutes while always keeping the
current database rows visible. The backend cache interval defaults to five
minutes for ordinary non-forced requests and can be changed with
`STOCK_DATA_CACHE_SECONDS`. Request `/stocks?refresh=1` to start a forced
background refresh.

## Requirements

- Python 3.10 or later
- Internet access when live market data is required

## Installation

```powershell
git clone https://github.com/reza-mohammadvand/Stocks.git
cd Stocks
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Running the application

### Windows Command Prompt

Open CMD in the project directory and run:

```cmd
run.cmd
```

The launcher uses the project's `.venv`, creates it when needed, installs any
missing requirements, and starts the server without opening a browser. The
default port is `5050`. A different port can be passed directly:

```cmd
run.cmd 6060
```

Then open `http://127.0.0.1:5050` (or the selected port) in a browser.

### Manual start

The default application port is `5050`:

```powershell
python app.py
```

Open:

```text
http://127.0.0.1:5050
```

To use another port in PowerShell:

```powershell
$env:STOCK_DASHBOARD_PORT = "6060"
python app.py
```

Enable Flask debug mode only during local development:

```powershell
$env:STOCK_DASHBOARD_DEBUG = "1"
python app.py
```

On Linux or macOS:

```bash
STOCK_DASHBOARD_PORT=6060 python app.py
```

## Project structure

```text
Stocks/
|-- app.py                         # Flask app and market-data services
|-- run.cmd                        # One-command Windows CMD launcher
|-- requirements.txt               # Python dependencies
|-- templates/
|   |-- indextest.html             # Current dashboard interface
|   `-- index.html                 # Preserved legacy view
|-- static/
|   |-- scripttest.js              # Current UI behaviour and analysis logic
|   |-- script.js                  # Preserved legacy UI script
|   |-- style.css                  # Base styles
|   |-- theme.css                  # Current glass theme and responsive layout
|   |-- Stocks.png                 # Hero image for the Stocks tab
|   |-- Options.png                # Hero image for the Options tab
|   |-- fonts/
|   |   |-- Vazirmatn-Variable.woff2
|   |   `-- OFL-Vazirmatn.txt
|   |-- logo.png
|   `-- iransans.ttf
`-- data/
    |-- stock_symbols.json          # Ordered symbol allow-list
    |-- stocks.db                    # SQLite stock catalogue and update metadata
    |-- trade_value_snapshot.json
    `-- order_book_snapshot.json
```

## Disclaimer

This project is an analysis and educational tool. It does not execute trades and does not constitute investment advice.
