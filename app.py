"""app.py - Flask application: pages, JSON search API and export routes."""
import io
import logging
import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_file

from export import to_csv_bytes, to_xlsx_bytes
from scraper import HARD_LIMIT, ScrapeError, search_businesses

load_dotenv()
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)


def _error(message, status=400):
    return jsonify({"status": "error", "message": message}), status


@app.route("/")
def index():
    return render_template("index.html", max_limit=HARD_LIMIT)


@app.route("/api/search", methods=["POST"])
def api_search():
    """Validate input, scrape Google Maps and return JSON results."""
    data = request.get_json(silent=True) or {}
    category = str(data.get("category", "")).strip()
    location = str(data.get("location", "")).strip()

    if not 2 <= len(category) <= 80:
        return _error("Business category must be 2-80 characters.")
    if not 2 <= len(location) <= 80:
        return _error("Location must be 2-80 characters.")
    try:
        max_results = int(data.get("max_results", 20))
    except (TypeError, ValueError):
        return _error("Maximum results must be a number.")
    if not 1 <= max_results <= HARD_LIMIT:
        return _error(f"Maximum results must be between 1 and {HARD_LIMIT}.")

    try:
        results = search_businesses(category, location, max_results)
    except ScrapeError as exc:
        app.logger.warning("Search failed: %s", exc)
        return _error(str(exc), exc.status_code)
    except Exception:  # never crash the server
        app.logger.exception("Unexpected error")
        return _error("Unexpected server error. Please try again.", 500)

    return jsonify({"status": "success", "total": len(results), "results": results})


def _rows_from_request():
    """Read the rows the browser wants exported (the current table)."""
    data = request.get_json(silent=True) or {}
    rows = data.get("results")
    if not isinstance(rows, list) or not rows:
        return None
    return [r for r in rows if isinstance(r, dict)][:500]


def _filename(ext):
    return f"leads_{datetime.now():%Y%m%d_%H%M%S}.{ext}"


@app.route("/api/export/csv", methods=["POST"])
def export_csv():
    rows = _rows_from_request()
    if not rows:
        return _error("No results to export. Run a search first.")
    return send_file(io.BytesIO(to_csv_bytes(rows)), mimetype="text/csv",
                     as_attachment=True, download_name=_filename("csv"))


@app.route("/api/export/xlsx", methods=["POST"])
def export_xlsx():
    rows = _rows_from_request()
    if not rows:
        return _error("No results to export. Run a search first.")
    return send_file(
        io.BytesIO(to_xlsx_bytes(rows)),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True, download_name=_filename("xlsx"))


if __name__ == "__main__":
    # Local use only: http://127.0.0.1:5000
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", 5000)),
            debug=os.getenv("FLASK_DEBUG") == "1")
