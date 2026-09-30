"""
Standalone Price Collector — No Redis / Celery required.

Run this in a separate terminal:
    python collect_prices.py

What it does every INTERVAL minutes:
  1. Searches Amazon for all queries in TRACK_QUERIES
  2. Saves/updates product listings in DB
  3. Records current price in price_history
  4. Compares with historical average and logs DEAL ALERTS
  5. Prints a summary table

Stop with Ctrl+C.
"""

import asyncio
import sys
from datetime import datetime

# ── Products to track ─────────────────────────────────────────────────────────
TRACK_QUERIES = [
    "iPhone 16 128GB",
    "Samsung Galaxy S24 128GB",
    "OnePlus 12 256GB",
    "Samsung 55 inch 4K TV",
    "Sony WH-1000XM5 headphones",
]

INTERVAL_MINUTES = 30        # collect every 30 minutes
DEAL_THRESHOLD_PCT = -5.0    # alert when 5%+ below historical average


async def collect_once():
    from app.database import AsyncSessionLocal
    from app.services.product_service import search_products
    from app.services.history_service import record_current_price
    from app.services.analysis_service import get_or_calculate_analysis
    from app.models.listing import ProductListing

    print(f"\n{'='*60}")
    print(f"  DealGuard Price Collector — {datetime.now().strftime('%d %b %Y %H:%M:%S')}")
    print(f"{'='*60}")

    deal_alerts = []

    for query in TRACK_QUERIES:
        print(f"\nSearching: {query}")
        try:
            async with AsyncSessionLocal() as db:
                results = await search_products(db, query)

            if not results:
                print(f"  No results found")
                continue

            for r in results[:2]:  # top 2 results per query
                listing_id = r.listing_id
                current_price = r.current_price
                title = (r.title or "")[:55]

                if not current_price:
                    print(f"  [{r.marketplace.upper()}] {title} — no price")
                    continue

                # Record the price
                async with AsyncSessionLocal() as db:
                    await record_current_price(
                        db=db,
                        listing_id=listing_id,
                        selling_price=current_price,
                        mrp=r.mrp,
                        effective_price=r.effective_price,
                        currency=r.currency or "INR",
                        source_type="price_collector",
                    )

                # Recalculate analysis
                async with AsyncSessionLocal() as db:
                    analysis = await get_or_calculate_analysis(
                        db, listing_id, force_recalculate=True
                    )

                if analysis:
                    pct = analysis.pct_vs_average or 0
                    hist_avg = analysis.historical_average or 0
                    classification = analysis.classification or "UNKNOWN"
                    trend = analysis.price_trend or ""
                    obs = analysis.observation_count or 0

                    sign = "+" if pct >= 0 else ""
                    alert = " *** DEAL ALERT ***" if pct <= DEAL_THRESHOLD_PCT else ""

                    print(
                        f"  [{r.marketplace.upper()}] {title}\n"
                        f"    Price: Rs.{current_price:,.0f}  "
                        f"Avg: Rs.{hist_avg:,.0f}  "
                        f"vs Avg: {sign}{pct:.1f}%  "
                        f"Trend: {trend}  "
                        f"Obs: {obs}"
                        f"{alert}"
                    )

                    if pct <= DEAL_THRESHOLD_PCT:
                        deal_alerts.append({
                            "title": r.title,
                            "price": current_price,
                            "avg": hist_avg,
                            "pct": pct,
                            "classification": classification,
                        })
                else:
                    print(f"  [{r.marketplace.upper()}] {title} — price: Rs.{current_price:,.0f} (no history yet)")

        except Exception as e:
            print(f"  ERROR for '{query}': {e}")

    # Deal summary
    if deal_alerts:
        print(f"\n{'*'*60}")
        print(f"  {len(deal_alerts)} DEAL(S) FOUND!")
        print(f"{'*'*60}")
        for d in deal_alerts:
            print(f"  {d['title'][:50]}")
            print(f"    Rs.{d['price']:,.0f}  ({d['pct']:+.1f}% vs avg Rs.{d['avg']:,.0f})  [{d['classification']}]")
    else:
        print(f"\n  No deals below {DEAL_THRESHOLD_PCT}% threshold this round.")

    print(f"\nNext collection in {INTERVAL_MINUTES} minutes. Press Ctrl+C to stop.")


async def main():
    print("DealGuard Price Collector starting...")
    print(f"Tracking {len(TRACK_QUERIES)} queries every {INTERVAL_MINUTES} minutes")
    print("Press Ctrl+C to stop\n")

    while True:
        try:
            await collect_once()
        except KeyboardInterrupt:
            print("\nStopped by user.")
            break
        except Exception as e:
            print(f"\nCollection error: {e}")

        try:
            await asyncio.sleep(INTERVAL_MINUTES * 60)
        except asyncio.CancelledError:
            break


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDealGuard Price Collector stopped.")
