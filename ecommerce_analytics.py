"""
E-commerce Sales Dashboard Backend
====================================
Analytics engine over multi-day e-commerce orders: daily/weekly/monthly
totals, top products, customer frequency, fraud-pattern detection,
percentiles, and week-over-week trend analysis.

Data shape
----------
orders = [
    {
        "order_id": "ORD001",
        "date": "2026-08-01",
        "customer": "CUST123",
        "items": [
            {"product": "Laptop", "quantity": 1, "price": 850},
            {"product": "Mouse", "quantity": 2, "price": 25},
        ],
    },
    ...
]

Design notes
------------
- Every order total requires a *nested* loop (orders -> items), since
  an order's value is the sum of quantity * price across its line
  items. `order_total()` is the single place that logic lives, so every
  other function (daily totals, top products, percentiles, fraud
  detection) reuses it instead of recomputing order value differently.
- Aggregation by day/week/month/product all follow the same pattern:
  loop over orders, compute a bucket key, accumulate into a dict. This
  keeps the four aggregation functions structurally consistent and easy
  to compare.
- Percentiles and week-over-week growth are computed with plain
  arithmetic (no numpy/pandas) so the module has zero third-party
  dependencies -- only `statistics` and `datetime` from the standard
  library.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

Order = Dict[str, object]
Item = Dict[str, object]


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------
def sample_orders() -> List[Order]:
    return [
        {"order_id": "ORD001", "date": "2026-08-01", "customer": "CUST123", "items": [
            {"product": "Laptop", "quantity": 1, "price": 850},
            {"product": "Mouse", "quantity": 2, "price": 25},
        ]},
        {"order_id": "ORD002", "date": "2026-08-01", "customer": "CUST456", "items": [
            {"product": "Keyboard", "quantity": 1, "price": 60},
        ]},
        {"order_id": "ORD003", "date": "2026-08-02", "customer": "CUST123", "items": [
            {"product": "Monitor", "quantity": 2, "price": 210},
            {"product": "Mouse", "quantity": 1, "price": 25},
        ]},
        {"order_id": "ORD004", "date": "2026-08-02", "customer": "CUST789", "items": [
            {"product": "Laptop", "quantity": 1, "price": 850},
        ]},
        {"order_id": "ORD005", "date": "2026-08-03", "customer": "CUST456", "items": [
            {"product": "Webcam", "quantity": 3, "price": 40},
            {"product": "Keyboard", "quantity": 1, "price": 60},
        ]},
        {"order_id": "ORD006", "date": "2026-08-04", "customer": "CUST123", "items": [
            {"product": "Mouse", "quantity": 5, "price": 25},
        ]},
        {"order_id": "ORD007", "date": "2026-08-05", "customer": "CUST999", "items": [
            {"product": "Laptop", "quantity": 4, "price": 850},  # unusually large order
        ]},
        {"order_id": "ORD008", "date": "2026-08-08", "customer": "CUST456", "items": [
            {"product": "Monitor", "quantity": 1, "price": 210},
        ]},
        {"order_id": "ORD009", "date": "2026-08-09", "customer": "CUST789", "items": [
            {"product": "Laptop", "quantity": 1, "price": 850},
            {"product": "Keyboard", "quantity": 1, "price": 60},
        ]},
        {"order_id": "ORD010", "date": "2026-08-10", "customer": "CUST123", "items": [
            {"product": "Webcam", "quantity": 1, "price": 40},
        ]},
        {"order_id": "ORD011", "date": "2026-08-15", "customer": "CUST456", "items": [
            {"product": "Laptop", "quantity": 2, "price": 850},
            {"product": "Monitor", "quantity": 2, "price": 210},
        ]},
        {"order_id": "ORD012", "date": "2026-08-16", "customer": "CUST999", "items": [
            {"product": "Mouse", "quantity": 2, "price": 25},
        ]},
        # Same customer, same day, three separate orders -> unusual-activity flag
        {"order_id": "ORD013", "date": "2026-08-17", "customer": "CUST321", "items": [
            {"product": "Keyboard", "quantity": 1, "price": 60},
        ]},
        {"order_id": "ORD014", "date": "2026-08-17", "customer": "CUST321", "items": [
            {"product": "Mouse", "quantity": 1, "price": 25},
        ]},
        {"order_id": "ORD015", "date": "2026-08-17", "customer": "CUST321", "items": [
            {"product": "Webcam", "quantity": 1, "price": 40},
        ]},
    ]


# ---------------------------------------------------------------------------
# Core order math (nested loop lives here, exactly once)
# ---------------------------------------------------------------------------
def order_total(order: Order) -> float:
    """Sum of quantity * price across every line item in one order."""
    total = 0.0
    for item in order["items"]:
        total += item["quantity"] * item["price"]
    return round(total, 2)


def _order_date(order: Order) -> date:
    return datetime.strptime(order["date"], "%Y-%m-%d").date()


def _iso_week_key(d: date) -> str:
    year, week, _ = d.isocalendar()
    return f"{year}-W{week:02d}"


def _month_key(d: date) -> str:
    return f"{d.year}-{d.month:02d}"


# ---------------------------------------------------------------------------
# Date-based filtering
# ---------------------------------------------------------------------------
def filter_orders_by_date(orders: List[Order], start_date: str, end_date: str) -> List[Order]:
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()

    filtered: List[Order] = []
    for order in orders:
        if start <= _order_date(order) <= end:
            filtered.append(order)
    return filtered


# ---------------------------------------------------------------------------
# Daily / weekly / monthly totals
# ---------------------------------------------------------------------------
def daily_totals(orders: List[Order]) -> Dict[str, float]:
    totals: Dict[str, float] = defaultdict(float)
    for order in orders:
        totals[order["date"]] += order_total(order)
    return {day: round(total, 2) for day, total in sorted(totals.items())}


def weekly_totals(orders: List[Order]) -> Dict[str, float]:
    totals: Dict[str, float] = defaultdict(float)
    for order in orders:
        key = _iso_week_key(_order_date(order))
        totals[key] += order_total(order)
    return {week: round(total, 2) for week, total in sorted(totals.items())}


def monthly_totals(orders: List[Order]) -> Dict[str, float]:
    totals: Dict[str, float] = defaultdict(float)
    for order in orders:
        key = _month_key(_order_date(order))
        totals[key] += order_total(order)
    return {month: round(total, 2) for month, total in sorted(totals.items())}


# ---------------------------------------------------------------------------
# Top-selling products (dictionary aggregation, nested loop)
# ---------------------------------------------------------------------------
def top_selling_products(orders: List[Order], top_n: int = 5) -> List[Tuple[str, Dict[str, float]]]:
    """
    Returns [(product_name, {"quantity_sold": int, "revenue": float}), ...]
    sorted by revenue, descending, top_n entries.
    """
    stats: Dict[str, Dict[str, float]] = defaultdict(lambda: {"quantity_sold": 0, "revenue": 0.0})

    for order in orders:
        for item in order["items"]:
            product = item["product"]
            stats[product]["quantity_sold"] += item["quantity"]
            stats[product]["revenue"] += item["quantity"] * item["price"]

    for product_stats in stats.values():
        product_stats["revenue"] = round(product_stats["revenue"], 2)

    ranked = sorted(stats.items(), key=lambda pair: pair[1]["revenue"], reverse=True)
    return ranked[:top_n]


# ---------------------------------------------------------------------------
# Customer purchase frequency
# ---------------------------------------------------------------------------
def customer_purchase_frequency(orders: List[Order]) -> Dict[str, int]:
    counts: Dict[str, int] = defaultdict(int)
    for order in orders:
        counts[order["customer"]] += 1
    return dict(sorted(counts.items(), key=lambda pair: pair[1], reverse=True))


def customer_total_spend(orders: List[Order]) -> Dict[str, float]:
    spend: Dict[str, float] = defaultdict(float)
    for order in orders:
        spend[order["customer"]] += order_total(order)
    return {c: round(v, 2) for c, v in sorted(spend.items(), key=lambda p: p[1], reverse=True)}


# ---------------------------------------------------------------------------
# Unusual-pattern / fraud detection
# ---------------------------------------------------------------------------
def detect_unusual_orders(orders: List[Order], value_threshold: float) -> List[Order]:
    """Orders whose total value is at/above `value_threshold`."""
    flagged: List[Order] = []
    for order in orders:
        if order_total(order) >= value_threshold:
            flagged.append(order)
    return flagged


def detect_unusual_customer_activity(
    orders: List[Order], max_orders_per_day: int = 2
) -> Dict[Tuple[str, str], int]:
    """
    Flags (customer, date) pairs where the same customer placed more
    than `max_orders_per_day` separate orders on the same day --
    a common signal of card-testing or account-takeover fraud.
    Returns {(customer, date): order_count, ...} for flagged pairs only.
    """
    daily_customer_orders: Dict[Tuple[str, str], int] = defaultdict(int)
    for order in orders:
        key = (order["customer"], order["date"])
        daily_customer_orders[key] += 1

    return {
        key: count
        for key, count in daily_customer_orders.items()
        if count > max_orders_per_day
    }


# ---------------------------------------------------------------------------
# Percentile calculations
# ---------------------------------------------------------------------------
def percentile(values: List[float], p: float) -> float:
    """
    Nearest-rank percentile of a list of numbers, 0 <= p <= 100.
    No third-party dependency; simple and adequate for dashboard use.
    """
    if not values:
        return 0.0
    if not 0 <= p <= 100:
        raise ValueError("Percentile must be between 0 and 100.")

    ordered = sorted(values)
    if p == 100:
        return round(ordered[-1], 2)

    rank = (p / 100) * (len(ordered) - 1)
    lower_index = int(rank)
    fraction = rank - lower_index

    if lower_index + 1 < len(ordered):
        interpolated = ordered[lower_index] + fraction * (
            ordered[lower_index + 1] - ordered[lower_index]
        )
    else:
        interpolated = ordered[lower_index]
    return round(interpolated, 2)


def order_value_percentiles(orders: List[Order], percentiles: List[float] = [50, 90, 95, 99]) -> Dict[str, float]:
    values = [order_total(o) for o in orders]
    return {f"p{int(p)}": percentile(values, p) for p in percentiles}


# ---------------------------------------------------------------------------
# Trend analysis: week-over-week growth
# ---------------------------------------------------------------------------
def week_over_week_growth(orders: List[Order]) -> Dict[str, Optional[float]]:
    """
    For each ISO week (sorted chronologically), returns % growth in
    revenue vs. the previous week. The first week has no prior week to
    compare against, so its growth is None.
    """
    weekly = weekly_totals(orders)
    weeks = list(weekly.keys())  # already sorted

    growth: Dict[str, Optional[float]] = {}
    previous_total: Optional[float] = None
    for week in weeks:
        current_total = weekly[week]
        if previous_total is None or previous_total == 0:
            growth[week] = None
        else:
            growth[week] = round(((current_total - previous_total) / previous_total) * 100, 2)
        previous_total = current_total
    return growth


# ---------------------------------------------------------------------------
# Combined dashboard report
# ---------------------------------------------------------------------------
def generate_dashboard_report(
    orders: List[Order],
    fraud_value_threshold: float = 2000,
    max_orders_per_day: int = 2,
) -> Dict[str, object]:
    return {
        "order_count": len(orders),
        "total_revenue": round(sum(order_total(o) for o in orders), 2),
        "daily_totals": daily_totals(orders),
        "weekly_totals": weekly_totals(orders),
        "monthly_totals": monthly_totals(orders),
        "top_products": top_selling_products(orders),
        "customer_frequency": customer_purchase_frequency(orders),
        "customer_spend": customer_total_spend(orders),
        "unusual_orders": detect_unusual_orders(orders, fraud_value_threshold),
        "unusual_customer_activity": {
            f"{customer} on {order_date}": count
            for (customer, order_date), count in detect_unusual_customer_activity(
                orders, max_orders_per_day
            ).items()
        },
        "order_value_percentiles": order_value_percentiles(orders),
        "week_over_week_growth": week_over_week_growth(orders),
    }


def print_dashboard_report(report: Dict[str, object]) -> None:
    print("=== E-commerce Sales Dashboard ===")
    print(f"Orders: {report['order_count']}   Total revenue: ${report['total_revenue']:,.2f}")

    print("\n-- Daily totals --")
    for day, total in report["daily_totals"].items():
        print(f"  {day}: ${total:,.2f}")

    print("\n-- Weekly totals --")
    for week, total in report["weekly_totals"].items():
        print(f"  {week}: ${total:,.2f}")

    print("\n-- Monthly totals --")
    for month, total in report["monthly_totals"].items():
        print(f"  {month}: ${total:,.2f}")

    print("\n-- Top-selling products --")
    for product, stats in report["top_products"]:
        print(f"  {product}: {stats['quantity_sold']} units, ${stats['revenue']:,.2f} revenue")

    print("\n-- Customer purchase frequency --")
    for customer, count in report["customer_frequency"].items():
        print(f"  {customer}: {count} order(s), ${report['customer_spend'][customer]:,.2f} spent")

    print(f"\n-- Unusual orders (>= ${2000:,.0f}) --")
    for order in report["unusual_orders"]:
        print(f"  {order['order_id']} on {order['date']} by {order['customer']}: "
              f"${order_total(order):,.2f}")

    print("\n-- Unusual customer activity (multiple orders same day) --")
    if not report["unusual_customer_activity"]:
        print("  None detected.")
    for label, count in report["unusual_customer_activity"].items():
        print(f"  {label}: {count} orders")

    print("\n-- Order value percentiles --")
    for label, value in report["order_value_percentiles"].items():
        print(f"  {label}: ${value:,.2f}")

    print("\n-- Week-over-week growth --")
    for week, growth in report["week_over_week_growth"].items():
        growth_str = "N/A" if growth is None else f"{growth:+.1f}%"
        print(f"  {week}: {growth_str}")


# ---------------------------------------------------------------------------
# Self-tests
# ---------------------------------------------------------------------------
def run_self_tests() -> None:
    orders = sample_orders()

    # order_total: nested-loop sum
    ord1_total = order_total(orders[0])
    assert ord1_total == 850 + 2 * 25, ord1_total

    # daily totals
    daily = daily_totals(orders)
    assert daily["2026-08-01"] == round((850 + 2 * 25) + 60, 2)

    # weekly totals: keys should be ISO year-week strings
    weekly = weekly_totals(orders)
    assert all("W" in k for k in weekly)
    assert sum(weekly.values()) == round(sum(order_total(o) for o in orders), 2)

    # monthly totals: single month in the sample data
    monthly = monthly_totals(orders)
    assert list(monthly.keys()) == ["2026-08"]

    # top products: Laptop should be #1 by revenue
    top = top_selling_products(orders, top_n=3)
    assert top[0][0] == "Laptop"

    # customer frequency
    freq = customer_purchase_frequency(orders)
    assert freq["CUST123"] == 4  # ORD001, ORD003, ORD006, ORD010
    assert freq["CUST321"] == 3

    # unusual single-order value (ORD007: 4 * 850 = 3400)
    unusual = detect_unusual_orders(orders, 2000)
    unusual_ids = {o["order_id"] for o in unusual}
    assert "ORD007" in unusual_ids
    assert "ORD001" not in unusual_ids

    # unusual same-day customer activity (CUST321 placed 3 orders on 2026-08-17)
    flagged = detect_unusual_customer_activity(orders, max_orders_per_day=2)
    assert ("CUST321", "2026-08-17") in flagged
    assert flagged[("CUST321", "2026-08-17")] == 3

    # percentiles: sanity checks
    values = [order_total(o) for o in orders]
    p50 = percentile(values, 50)
    p100 = percentile(values, 100)
    assert p100 == max(values)
    assert min(values) <= p50 <= max(values)

    # week-over-week growth: first week has no prior week
    growth = week_over_week_growth(orders)
    first_week = next(iter(growth))
    assert growth[first_week] is None

    # date filtering
    ranged = filter_orders_by_date(orders, "2026-08-01", "2026-08-05")
    assert all("2026-08-01" <= o["date"] <= "2026-08-05" for o in ranged)
    assert len(ranged) == 7

    # combined report has every expected key
    report = generate_dashboard_report(orders)
    for key in (
        "order_count", "total_revenue", "daily_totals", "weekly_totals",
        "monthly_totals", "top_products", "customer_frequency",
        "unusual_orders", "unusual_customer_activity",
        "order_value_percentiles", "week_over_week_growth",
    ):
        assert key in report

    print("All self-tests passed.")


def main() -> None:
    import sys

    if "--test" in sys.argv:
        run_self_tests()
        return

    orders = sample_orders()
    report = generate_dashboard_report(orders)
    print_dashboard_report(report)


if __name__ == "__main__":
    main()
