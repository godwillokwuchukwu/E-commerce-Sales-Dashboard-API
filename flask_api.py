"""
E-commerce Sales Dashboard API (Stretch Goal)
================================================
A thin Flask layer over `ecommerce_analytics.py` that serves the same
metrics as JSON, so a frontend dashboard can consume them over HTTP.

Run it:
    python3 flask_api.py
    # then visit http://127.0.0.1:5000/api/dashboard

All the actual analytics logic lives in ecommerce_analytics.py -- this
file only handles routing, query-param parsing, and JSON serialization.
"""

from __future__ import annotations

from flask import Flask, jsonify, request

import ecommerce_analytics as analytics

app = Flask(__name__)

# In a real service this would come from a database. For this project,
# each request re-reads the same in-memory sample data.
ORDERS = analytics.sample_orders()

# Every JSON endpoint this API serves, shown on the landing page below.
# (description, path) -- paths are relative, no query params included.
ENDPOINTS = [
    ("Health check", "/api/health"),
    ("Daily totals", "/api/daily-totals"),
    ("Weekly totals", "/api/weekly-totals"),
    ("Monthly totals", "/api/monthly-totals"),
    ("Top-selling products", "/api/top-products?top_n=5"),
    ("Customer purchase frequency", "/api/customer-frequency"),
    ("Customer total spend", "/api/customer-spend"),
    ("Fraud / unusual-activity alerts", "/api/fraud-alerts"),
    ("Order value percentiles", "/api/percentiles"),
    ("Week-over-week trend", "/api/trend"),
    ("Full dashboard report", "/api/dashboard"),
]


def _get_orders():
    """
    Apply optional ?start=YYYY-MM-DD&end=YYYY-MM-DD query params to
    scope every endpoint to a date range, defaulting to all orders.
    """
    start = request.args.get("start")
    end = request.args.get("end")
    if start and end:
        return analytics.filter_orders_by_date(ORDERS, start, end)
    return ORDERS


@app.get("/")
def index():
    """Simple landing page listing every available endpoint as a link."""
    rows = "\n".join(
        f'<li><a href="{path}"><code>{path}</code></a> — {label}</li>'
        for label, path in ENDPOINTS
    )
    html = f"""
    <!doctype html>
    <html>
    <head>
        <title>E-commerce Sales Dashboard API</title>
        <style>
            body {{ font-family: system-ui, sans-serif; max-width: 700px;
                    margin: 40px auto; line-height: 1.6; color: #222; }}
            h1 {{ font-size: 1.4rem; }}
            code {{ background: #f2f2f2; padding: 2px 6px; border-radius: 4px; }}
            li {{ margin-bottom: 6px; }}
            .note {{ color: #666; font-size: 0.9rem; margin-top: 24px; }}
        </style>
    </head>
    <body>
        <h1>E-commerce Sales Dashboard API</h1>
        <p>Available endpoints:</p>
        <ul>
            {rows}
        </ul>
        <p class="note">
            Every endpoint above also accepts
            <code>?start=YYYY-MM-DD&amp;end=YYYY-MM-DD</code> to scope results
            to a date range.
        </p>
    </body>
    </html>
    """
    return html


@app.get("/favicon.ico")
def favicon():
    # No favicon to serve; return an empty response instead of a 404.
    return "", 204


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/api/daily-totals")
def daily_totals():
    return jsonify(analytics.daily_totals(_get_orders()))


@app.get("/api/weekly-totals")
def weekly_totals():
    return jsonify(analytics.weekly_totals(_get_orders()))


@app.get("/api/monthly-totals")
def monthly_totals():
    return jsonify(analytics.monthly_totals(_get_orders()))


@app.get("/api/top-products")
def top_products():
    top_n = request.args.get("top_n", default=5, type=int)
    ranked = analytics.top_selling_products(_get_orders(), top_n=top_n)
    return jsonify([{"product": name, **stats} for name, stats in ranked])


@app.get("/api/customer-frequency")
def customer_frequency():
    return jsonify(analytics.customer_purchase_frequency(_get_orders()))


@app.get("/api/customer-spend")
def customer_spend():
    return jsonify(analytics.customer_total_spend(_get_orders()))


@app.get("/api/fraud-alerts")
def fraud_alerts():
    value_threshold = request.args.get("value_threshold", default=2000, type=float)
    max_per_day = request.args.get("max_orders_per_day", default=2, type=int)

    orders = _get_orders()
    unusual_orders = analytics.detect_unusual_orders(orders, value_threshold)
    unusual_activity = analytics.detect_unusual_customer_activity(orders, max_per_day)

    return jsonify({
        "unusual_orders": unusual_orders,
        "unusual_customer_activity": [
            {"customer": customer, "date": order_date, "order_count": count}
            for (customer, order_date), count in unusual_activity.items()
        ],
    })


@app.get("/api/percentiles")
def percentiles():
    return jsonify(analytics.order_value_percentiles(_get_orders()))


@app.get("/api/trend")
def trend():
    return jsonify(analytics.week_over_week_growth(_get_orders()))


@app.get("/api/dashboard")
def dashboard():
    """One-call endpoint returning the full combined report."""
    fraud_value_threshold = request.args.get("value_threshold", default=2000, type=float)
    max_per_day = request.args.get("max_orders_per_day", default=2, type=int)
    report = analytics.generate_dashboard_report(
        _get_orders(),
        fraud_value_threshold=fraud_value_threshold,
        max_orders_per_day=max_per_day,
    )
    return jsonify(report)


if __name__ == "__main__":
    app.run(debug=True)