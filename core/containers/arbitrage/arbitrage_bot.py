#!/usr/bin/env python3
"""
Multi-exchange crypto arbitrage scanner
- Pulls best bid/ask from several exchanges
- Normalizes quotes (USD, USDT, USDC -> USD-equivalent)
- Computes cross-exchange buy/sell spreads
- Adjusts for taker fees and slippage
- Prints top opportunities
- Optional: write CSV on each refresh

Exchanges implemented (public endpoints):
- Binance:      https://api.binance.com/api/v3/ticker/bookTicker?symbol={BASE}{QUOTE}
- Coinbase:     https://api.exchange.coinbase.com/products/{BASE}-{QUOTE}/ticker
- Kraken:       https://api.kraken.com/0/public/Ticker?pair={PAIR}
- KuCoin:       https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={BASE}-{QUOTE}
- Bitfinex:     https://api-pub.bitfinex.com/v2/ticker/t{BASE}{QUOTE}

Usage examples:
  python arbitrage_bot.py --symbols BTC,ETH --quotes USD,USDT --loops 1
  python arbitrage_bot.py --symbols BTC,ETH --quotes USD,USDT --interval 5 --min_spread_bps 10 --csv out.csv

Notes:
- Default "inventory_mode" assumes you already have inventory on each exchange, so no transfer/withdrawal costs are applied.
- If you plan to physically transfer coins between exchanges, set --inventory_mode 0 and configure withdrawal fees in config.
- All endpoints are public; heavy polling can trigger rate limits. Keep intervals sensible.
"""

import asyncio
import aiohttp
import time
import argparse
import math
import sys
import csv
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

USD_EQUIV = {
    "USD": 1.0,
    "USDT": 1.0,   # Adjust if you want to model a basis, e.g., 0.999
    "USDC": 1.0,
}

# Default taker fees (as decimal, e.g., 0.001 = 0.1%)
DEFAULT_TAKER_FEES = {
    "binance": 0.001,
    "coinbase": 0.006,     # coinbase exchange retail can be higher; adjust as needed
    "kraken": 0.0026,
    "kucoin": 0.001,
    "bitfinex": 0.002,
}

# Optional withdrawal fees in QUOTE currency for transfer mode (very rough placeholders)
# For inventory_mode=1 these are ignored.
WITHDRAWAL_FEES = {
    # Example: withdrawing USDT on TRON often ~1 USDT; set per your route
    "binance": {"USDT": 1.0, "USDC": 1.0, "USD": 0.0},
    "coinbase": {"USDT": 1.0, "USDC": 1.0, "USD": 0.0},
    "kraken": {"USDT": 5.0, "USDC": 5.0, "USD": 0.0},
    "kucoin": {"USDT": 1.0, "USDC": 1.0, "USD": 0.0},
    "bitfinex": {"USDT": 5.0, "USDC": 5.0, "USD": 0.0},
}

@dataclass
class Quote:
    bid: float   # price you can sell at on this exchange
    ask: float   # price you can buy at on this exchange
    ts: float    # epoch seconds
    base: str
    quote: str

class ExchangeClient:
    name: str

    def __init__(self, session: aiohttp.ClientSession, taker_fee: float):
        self.session = session
        self.taker_fee = taker_fee

    async def fetch_quote(self, base: str, quote: str) -> Optional[Quote]:
        raise NotImplementedError

class BinanceClient(ExchangeClient):
    name = "binance"

    async def fetch_quote(self, base: str, quote: str) -> Optional[Quote]:
        symbol = f"{base}{quote}"
        url = f"https://api.binance.com/api/v3/ticker/bookTicker?symbol={symbol}"
        try:
            async with self.session.get(url, timeout=10) as r:
                if r.status != 200:
                    return None
                j = await r.json()
                bid = float(j["bidPrice"])
                ask = float(j["askPrice"])
                return Quote(bid=bid, ask=ask, ts=time.time(), base=base, quote=quote)
        except Exception:
            return None

class CoinbaseClient(ExchangeClient):
    name = "coinbase"

    async def fetch_quote(self, base: str, quote: str) -> Optional[Quote]:
        product = f"{base}-{quote}"
        url = f"https://api.exchange.coinbase.com/products/{product}/ticker"
        headers = {"User-Agent": "arbitrage-bot/1.0"}
        try:
            async with self.session.get(url, timeout=10, headers=headers) as r:
                if r.status != 200:
                    return None
                j = await r.json()
                # Response fields: price, bid, ask, volume, time
                bid = float(j.get("bid") or j.get("price"))
                ask = float(j.get("ask") or j.get("price"))
                return Quote(bid=bid, ask=ask, ts=time.time(), base=base, quote=quote)
        except Exception:
            return None

class KrakenClient(ExchangeClient):
    name = "kraken"

    # Kraken pairs are special: BTC/USD -> XBTUSD typically
    # We support a minimal mapping for common assets.
    KR_MAP = {
        ("BTC","USD"): "XBTUSD",
        ("ETH","USD"): "ETHUSD",
        ("BTC","USDT"): "XBTUSDT",
        ("ETH","USDT"): "ETHUSDT",
        ("BTC","USDC"): "XBTUSDC",
        ("ETH","USDC"): "ETHUSDC",
    }

    async def fetch_quote(self, base: str, quote: str) -> Optional[Quote]:
        pair = self.KR_MAP.get((base, quote))
        if not pair:
            return None
        url = f"https://api.kraken.com/0/public/Ticker?pair={pair}"
        try:
            async with self.session.get(url, timeout=10) as r:
                if r.status != 200:
                    return None
                j = await r.json()
                if j.get("error"):
                    return None
                # The result dict key can be alias or pair
                res = next(iter(j["result"].values()))
                ask = float(res["a"][0])
                bid = float(res["b"][0])
                return Quote(bid=bid, ask=ask, ts=time.time(), base=base, quote=quote)
        except Exception:
            return None

class KuCoinClient(ExchangeClient):
    name = "kucoin"

    async def fetch_quote(self, base: str, quote: str) -> Optional[Quote]:
        symbol = f"{base}-{quote}"
        url = f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={symbol}"
        try:
            async with self.session.get(url, timeout=10) as r:
                if r.status != 200:
                    return None
                j = await r.json()
                if j.get("code") != "200000":
                    return None
                data = j["data"]
                bid = float(data["bestBid"])
                ask = float(data["bestAsk"])
                return Quote(bid=bid, ask=ask, ts=time.time(), base=base, quote=quote)
        except Exception:
            return None

class BitfinexClient(ExchangeClient):
    name = "bitfinex"

    async def fetch_quote(self, base: str, quote: str) -> Optional[Quote]:
        symbol = f"t{base}{quote}"
        url = f"https://api-pub.bitfinex.com/v2/ticker/{symbol}"
        try:
            async with self.session.get(url, timeout=10) as r:
                if r.status != 200:
                    return None
                arr = await r.json()
                # Response: [ BID, BID_SIZE, ASK, ASK_SIZE, DAILY_CHANGE, ... ]
                bid = float(arr[0])
                ask = float(arr[2])
                return Quote(bid=bid, ask=ask, ts=time.time(), base=base, quote=quote)
        except Exception:
            return None

EXCHANGE_CLASSES = [
    BinanceClient,
    CoinbaseClient,
    KrakenClient,
    KuCoinClient,
    BitfinexClient,
]

def usd_equiv(price: float, quote: str) -> float:
    factor = USD_EQUIV.get(quote.upper())
    if factor is None:
        return math.nan
    return price * factor

def net_buy_price(ask: float, taker_fee: float, slippage: float) -> float:
    # Buy at ask, pay taker fee and allow slippage
    return ask * (1 + taker_fee) * (1 + slippage)

def net_sell_price(bid: float, taker_fee: float, slippage: float) -> float:
    # Sell at bid, pay taker fee and allow slippage
    return bid * (1 - taker_fee) * (1 - slippage)

async def fetch_all(session, symbols: List[str], quotes: List[str], taker_fees: Dict[str, float]) -> Dict[Tuple[str,str], Dict[str, Quote]]:
    results: Dict[Tuple[str,str], Dict[str, Quote]] = {}
    tasks = []
    clients = [cls(session, taker_fees.get(cls.name, 0.001)) for cls in EXCHANGE_CLASSES]

    for base in symbols:
        for quote in quotes:
            for client in clients:
                tasks.append(asyncio.create_task(_fetch_one(client, base, quote, results)))

    await asyncio.gather(*tasks, return_exceptions=True)
    return results

async def _fetch_one(client: ExchangeClient, base: str, quote: str, results: Dict[Tuple[str,str], Dict[str, Quote]]):
    q = await client.fetch_quote(base, quote)
    if q is None:
        return
    key = (base, quote)
    if key not in results:
        results[key] = {}
    results[key][client.name] = q

def compute_arbs(
    book: Dict[Tuple[str,str], Dict[str, Quote]],
    taker_fees: Dict[str, float],
    min_spread_bps: float,
    slippage: float,
    inventory_mode: bool,
    withdrawal_fees: Dict[str, Dict[str, float]],
    notional: float,
) -> List[Dict]:
    """Return list of arbitrage opportunities sorted by net spread desc.
    Spread formula (USD terms):
      buy on A at net_buy_price, sell on B at net_sell_price
      net_spread_pct = (sell_price_B - buy_price_A) / buy_price_A * 100
    If inventory_mode is False, subtract approximate withdrawal fee on the quote asset from proceeds.
    """
    opps = []
    for (base, quote), quotes_by_exch in book.items():
        if quote.upper() not in USD_EQUIV:
            continue
        # Build list of (exchange, bid, ask)
        rows = []
        for ex, q in quotes_by_exch.items():
            bid_usd = usd_equiv(q.bid, quote)
            ask_usd = usd_equiv(q.ask, quote)
            if math.isnan(bid_usd) or math.isnan(ask_usd):
                continue
            rows.append((ex, bid_usd, ask_usd))
        if len(rows) < 2:
            continue

        # Compute best sell and best buy across exchanges
        for ex_buy, bid_b, ask_b in rows:
            for ex_sell, bid_s, ask_s in rows:
                if ex_buy == ex_sell:
                    continue
                buy_net = net_buy_price(ask_b, taker_fees.get(ex_buy, 0.001), slippage)
                sell_net = net_sell_price(bid_s, taker_fees.get(ex_sell, 0.001), slippage)

                # Transfer costs if not inventory_mode
                transfer_cost = 0.0
                if not inventory_mode:
                    wf = withdrawal_fees.get(ex_buy, {}).get(quote.upper(), 0.0)
                    transfer_cost = wf  # in quote units ~ USD-equivalent
                # Profit in USD terms for 'notional' quote amount trade
                # You buy base for 'notional' worth at buy_net, receive qty_base = notional / buy_net
                qty_base = notional / buy_net
                gross_proceeds = qty_base * sell_net
                net_proceeds = gross_proceeds - (transfer_cost if not inventory_mode else 0.0)
                pnl = net_proceeds - notional
                spread_pct = pnl / notional * 100.0
                spread_bps = spread_pct * 100.0

                if spread_bps >= min_spread_bps:
                    opps.append({
                        "symbol": f"{base}/{quote}",
                        "buy_ex": ex_buy,
                        "sell_ex": ex_sell,
                        "buy_price": round(buy_net, 4),
                        "sell_price": round(sell_net, 4),
                        "spread_pct": round(spread_pct, 4),
                        "spread_bps": round(spread_bps, 2),
                    })
    # Sort by highest spread
    opps.sort(key=lambda x: x["spread_bps"], reverse=True)
    return opps

def fmt_table(opps: List[Dict], limit: int = 15) -> str:
    cols = ["symbol","buy_ex","sell_ex","buy_price","sell_price","spread_bps","spread_pct"]
    widths = {c: len(c) for c in cols}
    for row in opps[:limit]:
        for c in cols:
            widths[c] = max(widths[c], len(str(row[c])))
    header = " | ".join(c.ljust(widths[c]) for c in cols)
    sep = "-+-".join("-"*widths[c] for c in cols)
    lines = [header, sep]
    for row in opps[:limit]:
        lines.append(" | ".join(str(row[c]).ljust(widths[c]) for c in cols))
    return "\n".join(lines)

async def main():
    ap = argparse.ArgumentParser(description="Cross-exchange arbitrage scanner")
    ap.add_argument("--symbols", type=str, default="BTC,ETH", help="Comma list of base assets")
    ap.add_argument("--quotes", type=str, default="USD,USDT,USDC", help="Comma list of quote assets")
    ap.add_argument("--interval", type=float, default=8.0, help="Seconds between scans")
    ap.add_argument("--loops", type=int, default=1, help="Number of iterations (use large for continuous)")
    ap.add_argument("--min_spread_bps", type=float, default=5.0, help="Minimum net spread in bps to show")
    ap.add_argument("--slippage_bps", type=float, default=3.0, help="Slippage model in bps per leg")
    ap.add_argument("--inventory_mode", type=int, default=1, help="1 = inventory on both sides, 0 = include withdrawal cost")
    ap.add_argument("--csv", type=str, default="", help="Optional CSV output path for appends")
    ap.add_argument("--notional", type=float, default=1000.0, help="Trade notional in quote currency units (USD equiv)")
    args = ap.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    quotes = [q.strip().upper() for q in args.quotes.split(",") if q.strip()]
    taker_fees = DEFAULT_TAKER_FEES.copy()
    slippage = args.slippage_bps / 10000.0
    inventory_mode = bool(args.inventory_mode)

    csv_path = args.csv.strip()
    csv_writer = None
    csv_file = None
    if csv_path:
        csv_file = open(csv_path, "a", newline="")
        csv_writer = csv.writer(csv_file)
        if csv_file.tell() == 0:
            csv_writer.writerow(["ts","symbol","buy_ex","sell_ex","buy_price","sell_price","spread_bps","spread_pct"])

    async with aiohttp.ClientSession() as session:
        for i in range(args.loops):
            t0 = time.time()
            try:
                book = await fetch_all(session, symbols, quotes, taker_fees)
                opps = compute_arbs(
                    book=book,
                    taker_fees=taker_fees,
                    min_spread_bps=args.min_spread_bps,
                    slippage=slippage,
                    inventory_mode=inventory_mode,
                    withdrawal_fees=WITHDRAWAL_FEES,
                    notional=args.notional,
                )
                print(f"\n=== Scan {i+1} @ {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} ===")
                if opps:
                    table = fmt_table(opps, limit=20)
                    print(table)
                    if csv_writer:
                        for row in opps:
                            csv_writer.writerow([int(t0), row["symbol"], row["buy_ex"], row["sell_ex"], row["buy_price"], row["sell_price"], row["spread_bps"], row["spread_pct"]])
                        csv_file.flush()
                else:
                    print("No opportunities above threshold.")
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
            # pacing
            dt = time.time() - t0
            sleep_s = max(0.0, args.interval - dt)
            if i < args.loops - 1:
                await asyncio.sleep(sleep_s)

    if csv_file:
        csv_file.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError:
        # Fallback for nested event loops (e.g., Jupyter)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
