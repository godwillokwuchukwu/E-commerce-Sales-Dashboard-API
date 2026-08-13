"""
Customer Transaction Analyzer
==============================
Analyzes a microfinance bank's daily customer transactions to surface
volume, averages, activity, and fraud-threshold alerts.

Data shape
----------
transactions = [
    {"customer": "Alice", "amount": 5000, "type": "transfer", "date": "2026-08-01"},
    {"customer": "Bob",   "amount": 75000, "type": "withdrawal", "date": "2026-08-01"},
    ...
]

Design notes
------------
- Metrics are computed with plain `for` loops (as required) rather than
  one-liner comprehensions everywhere, so the accumulation logic is
  explicit and easy to follow/debug.
- Every metric function takes a `transactions` list as its only
  required argument, so they compose cleanly: filter first (by date,
  by customer), then feed the filtered list into any metric function.
- `generate_report` ties every metric together into a single dict,
  which both the console printer and the CSV exporter consume, so the
  "shape of a report" is defined in exactly one place.
"""

from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

Transaction = Dict[str, object]

FRAUD_THRESHOLD = 50_000


# ---------------------------------------------------------------------------
# 1. Sample data
# ---------------------------------------------------------------------------
def sample_transactions() -> List[Transaction]:
    return [
        {"customer": "Alice", "amount": 5000, "type": "transfer", "date": "2026-08-01"},
        {"customer": "Bob", "amount": 75000, "type": "withdrawal", "date": "2026-08-01"},
        {"customer": "Alice", "amount": 3000, "type": "deposit", "date": "2026-08-01"},
        {"customer": "Chidi", "amount": 12000, "type": "transfer", "date": "2026-08-02"},
        {"customer": "Bob", "amount": 2000, "type": "deposit", "date": "2026-08-02"},
        {"customer": "Alice", "amount": 60000, "type": "withdrawal", "date": "2026-08-02"},
        {"customer": "Fatima", "amount": 8000, "type": "transfer", "date": "2026-08-03"},
        {"customer": "Chidi", "amount": 15000, "type": "transfer", "date": "2026-08-03"},
        {"customer": "Bob", "amount": 90000, "type": "withdrawal", "date": "2026-08-03"},
        {"customer": "Fatima", "amount": 4500, "type": "deposit", "date": "2026-08-04"},
        {"customer": "Alice", "amount": 7000, "type": "transfer", "date": "2026-08-04"},
        {"customer": "Chidi", "amount": 52000, "type": "withdrawal", "date": "2026-08-04"},
        {"customer": "Fatima", "amount": 3000, "type": "transfer", "date": "2026-08-05"},
        {"customer": "Bob", "amount": 6000, "type": "deposit", "date": "2026-08-05"},
    ]


# ---------------------------------------------------------------------------
# 2. Metric functions (each uses an explicit loop)
# ---------------------------------------------------------------------------
def total_transaction_count(transactions: List[Transaction]) -> int:
    count = 0
    for _ in transactions:
        count += 1
    return count


def total_transaction_volume(transactions: List[Transaction]) -> float:
    total = 0.0
    for txn in transactions:
        total += txn["amount"]
    return round(total, 2)


def average_transaction_value(transactions: List[Transaction]) -> float:
    count = total_transaction_count(transactions)
    if count == 0:
        return 0.0
    return round(total_transaction_volume(transactions) / count, 2)


def flag_fraud_transactions(
    transactions: List[Transaction], threshold: float = FRAUD_THRESHOLD
) -> List[Transaction]:
    """Transactions at or above the fraud threshold."""
    flagged: List[Transaction] = []
    for txn in transactions:
        if txn["amount"] >= threshold:
            flagged.append(txn)
    return flagged


def most_frequent_transaction_type(transactions: List[Transaction]) -> Optional[str]:
    type_counts: Dict[str, int] = {}
    for txn in transactions:
        t = txn["type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    if not type_counts:
        return None

    most_common_type = None
    highest_count = -1
    for txn_type, count in type_counts.items():
        if count > highest_count:
            highest_count = count
            most_common_type = txn_type
    return most_common_type


def most_active_customers(transactions: List[Transaction], top_n: int = 3) -> List[tuple]:
    """Return [(customer, transaction_count), ...] sorted descending, top_n entries."""
    activity: Dict[str, int] = {}
    for txn in transactions:
        c = txn["customer"]
        activity[c] = activity.get(c, 0) + 1

    ranked = sorted(activity.items(), key=lambda pair: pair[1], reverse=True)
    return ranked[:top_n]


# ---------------------------------------------------------------------------
# Improvements: date filtering + grouping by customer
# ---------------------------------------------------------------------------
def filter_by_date(
    transactions: List[Transaction], start_date: str, end_date: str
) -> List[Transaction]:
    """
    Keep only transactions with 'date' in the inclusive range
    [start_date, end_date]. Dates are ISO strings, e.g. '2026-08-01'.
    """
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()

    filtered: List[Transaction] = []
    for txn in transactions:
        txn_date = datetime.strptime(txn["date"], "%Y-%m-%d").date()
        if start <= txn_date <= end:
            filtered.append(txn)
    return filtered


def group_by_customer(transactions: List[Transaction]) -> Dict[str, List[Transaction]]:
    groups: Dict[str, List[Transaction]] = {}
    for txn in transactions:
        c = txn["customer"]
        groups.setdefault(c, []).append(txn)
    return groups


# ---------------------------------------------------------------------------
# 3. Report generator
# ---------------------------------------------------------------------------
def generate_report(
    transactions: List[Transaction], threshold: float = FRAUD_THRESHOLD
) -> Dict[str, object]:
    fraud_alerts = flag_fraud_transactions(transactions, threshold)

    return {
        "total_transaction_count": total_transaction_count(transactions),
        "total_volume": total_transaction_volume(transactions),
        "average_value": average_transaction_value(transactions),
        "most_frequent_type": most_frequent_transaction_type(transactions),
        "most_active_customers": most_active_customers(transactions),
        "fraud_threshold": threshold,
        "fraud_alert_count": len(fraud_alerts),
        "fraud_alerts": fraud_alerts,
    }


def print_report(report: Dict[str, object]) -> None:
    print("=== Transaction Summary Report ===")
    print(f"Total transactions : {report['total_transaction_count']}")
    print(f"Total volume       : ₦{report['total_volume']:,.2f}")
    print(f"Average value      : ₦{report['average_value']:,.2f}")
    print(f"Most frequent type : {report['most_frequent_type']}")

    print("\nMost active customers:")
    for customer, count in report["most_active_customers"]:
        print(f"  {customer}: {count} transaction(s)")

    print(f"\nFraud alerts (>= ₦{report['fraud_threshold']:,.0f}): "
          f"{report['fraud_alert_count']}")
    for txn in report["fraud_alerts"]:
        print(f"  {txn['date']}  {txn['customer']:<8} ₦{txn['amount']:>10,.2f}  ({txn['type']})")


# ---------------------------------------------------------------------------
# Improvement: export report to CSV
# ---------------------------------------------------------------------------
def export_report_to_csv(report: Dict[str, object], path: str | Path) -> None:
    """
    Writes a two-part CSV: summary metrics, then a table of flagged
    fraud-alert transactions.
    """
    path = Path(path)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)

        writer.writerow(["Metric", "Value"])
        writer.writerow(["Total transaction count", report["total_transaction_count"]])
        writer.writerow(["Total volume", report["total_volume"]])
        writer.writerow(["Average value", report["average_value"]])
        writer.writerow(["Most frequent type", report["most_frequent_type"]])
        writer.writerow(["Fraud threshold", report["fraud_threshold"]])
        writer.writerow(["Fraud alert count", report["fraud_alert_count"]])

        writer.writerow([])
        writer.writerow(["Most Active Customers", "Transaction Count"])
        for customer, count in report["most_active_customers"]:
            writer.writerow([customer, count])

        writer.writerow([])
        writer.writerow(["Fraud Alert Transactions"])
        writer.writerow(["Date", "Customer", "Amount", "Type"])
        for txn in report["fraud_alerts"]:
            writer.writerow([txn["date"], txn["customer"], txn["amount"], txn["type"]])


# ---------------------------------------------------------------------------
# 4. Tests with different data sets
# ---------------------------------------------------------------------------
def run_self_tests() -> None:
    data = sample_transactions()

    assert total_transaction_count(data) == 14
    assert total_transaction_volume(data) == sum(t["amount"] for t in data)
    assert average_transaction_value(data) == round(
        total_transaction_volume(data) / 14, 2
    )

    fraud = flag_fraud_transactions(data, 50_000)
    assert all(t["amount"] >= 50_000 for t in fraud)
    assert len(fraud) == 4  # Bob 75000, Bob 90000, Chidi 52000, Alice 60000

    most_type = most_frequent_transaction_type(data)
    assert most_type in ("transfer", "withdrawal", "deposit")

    top_customers = most_active_customers(data, top_n=2)
    assert len(top_customers) == 2
    assert top_customers[0][1] >= top_customers[1][1]

    ranged = filter_by_date(data, "2026-08-01", "2026-08-02")
    assert all("2026-08-01" <= t["date"] <= "2026-08-02" for t in ranged)
    assert len(ranged) == 6

    grouped = group_by_customer(data)
    assert set(grouped.keys()) == {"Alice", "Bob", "Chidi", "Fatima"}
    assert len(grouped["Alice"]) == 4

    # Edge case: empty dataset
    empty_report = generate_report([])
    assert empty_report["total_transaction_count"] == 0
    assert empty_report["average_value"] == 0.0
    assert empty_report["fraud_alerts"] == []

    # Edge case: single-transaction dataset
    single = [{"customer": "Zainab", "amount": 51000, "type": "withdrawal", "date": "2026-08-06"}]
    single_report = generate_report(single)
    assert single_report["total_transaction_count"] == 1
    assert single_report["fraud_alert_count"] == 1
    assert single_report["most_frequent_type"] == "withdrawal"

    # CSV export round-trip (file gets created and has expected header)
    report = generate_report(data)
    tmp_path = Path("_txn_report_selftest.csv")
    export_report_to_csv(report, tmp_path)
    content = tmp_path.read_text()
    assert "Total transaction count" in content
    assert "Fraud Alert Transactions" in content
    tmp_path.unlink(missing_ok=True)

    print("All self-tests passed.")


def main() -> None:
    import sys

    if "--test" in sys.argv:
        run_self_tests()
        return

    transactions = sample_transactions()

    report = generate_report(transactions)
    print_report(report)

    print("\n\n=== Filtered report: 2026-08-01 to 2026-08-03 ===")
    filtered = filter_by_date(transactions, "2026-08-01", "2026-08-03")
    print_report(generate_report(filtered))

    print("\n\n=== Grouped by customer (transaction counts) ===")
    for customer, txns in group_by_customer(transactions).items():
        print(f"  {customer}: {len(txns)} transaction(s), "
              f"total ₦{total_transaction_volume(txns):,.2f}")

    csv_path = "transaction_report.csv"
    export_report_to_csv(report, csv_path)
    print(f"\nReport exported to {csv_path!r}")


if __name__ == "__main__":
    main()
