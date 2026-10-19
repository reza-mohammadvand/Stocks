# Stock Market Watch

Stock Market Watch is a Persian, right-to-left dashboard for analysing the Iranian stock market. The current application uses options data to estimate market expectations for underlying stocks and includes a separate stock catalogue that can be expanded with additional indicators over time.

## Current interface

The dashboard has two main tabs:

- **Stocks**, the default first tab, reads immediately from SQLite and refreshes company, industry, and market-value data from TSETMC in the background.
- **Options** presents option-based market-expectation analysis.

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
- Calculates separate buy-side and sell-side value, volume, and order-count totals across the first five order-book levels for every symbol.
- Stores the latest complete catalogue in `data/stocks.db` and serves it immediately on page load.
- Replaces the SQLite rows atomically only after a background refresh is ready, so the table never disappears while online data is loading.
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
- Uses a responsive glass-style interface with Persian typography and right-to-left controls.

## Data endpoints

| Endpoint | Purpose |
|---|---|
| `/market-expectations` | Option-based market-expectation analysis |
| `/option-bases` | Underlying-symbol discovery and option-root mapping |
| `/stocks` | SQLite-backed online stock catalogue and trading indicators for the configured symbols |
| `/data` | Preserved data service for the former Market view |
| `/spread-data` | Preserved Bull Call Spread data and calculations |

Local snapshots are stored in:

- `data/trade_value_snapshot.json`
- `data/order_book_snapshot.json`

The stock catalogue is stored in `data/stocks.db`. The server checks for an
online refresh every five minutes by default while always returning the current
database rows immediately. Set `STOCK_DATA_CACHE_SECONDS` to change that
interval, or request `/stocks?refresh=1` to start a background refresh.

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
