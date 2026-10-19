const fs = require("fs");
const path = require("path");

const output = path.join(__dirname, "data", "rahavard_live_quotes.json");
const assetIds = new Set([
  "2",
  "43157",
  "1560",
  "2016",
  "2017",
  "35945",
  "44055",
]);

let quotes = {};
try {
  quotes = JSON.parse(fs.readFileSync(output, "utf8"));
} catch {
  quotes = {};
}

function saveQuotes() {
  const temporary = `${output}.tmp`;
  fs.writeFileSync(temporary, JSON.stringify(quotes));
  fs.renameSync(temporary, output);
}

function quotePayload(data) {
  return data?.last_trade || data?.trade || data?.value || data?.data || data;
}

function connect() {
  const socket = new WebSocket(
    "wss://rahavard365.com/api/v2/livedata/?EIO=4&transport=websocket",
  );

  socket.onmessage = (event) => {
    const frame = String(event.data);
    if (frame.startsWith("0")) {
      socket.send("40");
      return;
    }
    if (frame === "2") {
      socket.send("3");
      return;
    }
    if (frame.startsWith("40")) {
      for (const assetId of assetIds) {
        socket.send(
          `42["/join-asset-last_trade","exchange.asset[${assetId}]:asset-last_trade"]`,
        );
        socket.send(
          `42["/join-sidebar-last_value","exchange.asset[${assetId}]:sidebar-last_value"]`,
        );
      }
      return;
    }
    if (!frame.startsWith("42")) return;

    try {
      const [name, data] = JSON.parse(frame.slice(2));
      const payload = quotePayload(data);
      const assetId = String(
        payload?.entity_id
          ?? payload?.asset_id
          ?? payload?.id
          ?? data?.entity_id
          ?? data?.asset_id
          ?? data?.id
          ?? "",
      );
      if (
        (name !== "/asset-last_trade" && name !== "/sidebar-last_value")
        || !assetIds.has(assetId)
      ) {
        return;
      }

      const price = Number(
        payload?.real_close_price
          || payload?.close_price
          || payload?.last_price
          || payload?.price,
      );
      if (!(price > 0)) return;

      const priceChange = payload?.real_close_price_change
        ?? payload?.close_price_change
        ?? payload?.price_change
        ?? null;
      const changePercent = payload?.real_close_price_change_percent
        ?? payload?.close_price_change_percent
        ?? payload?.price_change_percent
        ?? payload?.change_percent
        ?? null;
      quotes[assetId] = {
        price,
        price_change: priceChange == null ? null : Number(priceChange),
        change_percent: changePercent == null ? null : Number(changePercent),
        market_time: payload?.end_date_time
          || payload?.date_time
          || payload?.last_trade_time
          || null,
        fetched_at: Math.floor(Date.now() / 1000),
      };
      saveQuotes();
    } catch {
      // Ignore malformed frames and keep the last valid quote.
    }
  };

  socket.onclose = () => setTimeout(connect, 1500);
  socket.onerror = () => socket.close();
}

connect();
