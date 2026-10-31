"""MarketSpace Enterprise Core Systems - Dynamic Backend
Python 3 standard library only (http.server + sqlite3). No external installs required.

REST API:
  GET    /api/products        -> list all products
  POST   /api/products        -> create product (requires X-Admin-Key header)
  DELETE /api/products/<id>   -> delete product (requires X-Admin-Key header)
  GET    /api/health          -> service status
"""

import json
import os
import re
import sqlite3
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PROJECT_ROOT, "marketspace.db")
ADMIN_KEY = os.environ.get("MARKETSPACE_ADMIN_KEY", "ms_enterprise_2026")
PORT = int(os.environ.get("PORT", "8080"))

DEFAULT_CATALOG = [
    { "name": "QuantumPro Titanium Laptop", "category": "electronics", "basePriceUSD": 2499.00, "specs": "16-Inch OLED, M4 Ultra Equivalent Chip, 64GB RAM, 2TB SSD", "image": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=600&auto=format&fit=crop&q=80" },
    { "name": "AeroSound Spatial Headphones", "category": "electronics", "basePriceUSD": 549.00, "specs": "Beryllium Dual Drivers, Adaptive ANC, 60-Hour Runtime", "image": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&auto=format&fit=crop&q=80" },
    { "name": "ScandiCraft Walnut Modular Sofa", "category": "furniture", "basePriceUSD": 3850.00, "specs": "Aniline Leather, Interlocked Frame: 280cm x 110cm", "image": "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=600&auto=format&fit=crop&q=80" },
    { "name": "Minimalist Marble Dining Table", "category": "furniture", "basePriceUSD": 1950.00, "specs": "Calacatta Marble Surface, Matte Black Steel Core: 220cm", "image": "https://images.unsplash.com/photo-1615066390971-03e4e1c36ddf?w=600&auto=format&fit=crop&q=80" },
]


def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            basePriceUSD REAL NOT NULL,
            specs TEXT NOT NULL,
            image TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    if count == 0:
        for item in DEFAULT_CATALOG:
            conn.execute(
                "INSERT INTO products (name, category, basePriceUSD, specs, image) VALUES (?,?,?,?,?)",
                (item["name"], item["category"], item["basePriceUSD"], item["specs"], item["image"]),
            )
        conn.commit()
    conn.close()


class MarketSpaceHandler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("HTTP %s - %s" % (self.address_string(), fmt % args), flush=True)

    def _send_json(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            return self._send_json(200, {"status": "ok", "service": "MarketSpace Enterprise Core Systems"})
        if parsed.path == "/api/products":
            conn = get_db()
            rows = conn.execute(
                "SELECT id, name, category, basePriceUSD, specs, image FROM products ORDER BY id"
            ).fetchall()
            conn.close()
            return self._send_json(200, [dict(r) for r in rows])
        if parsed.path == "/":
            self.send_response(302)
            self.send_header("Location", "/market%20space.html")
            self.end_headers()
            return
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/products":
            if self.headers.get("X-Admin-Key") != ADMIN_KEY:
                return self._send_json(401, {"error": "Unauthorized"})
            try:
                length = int(self.headers.get("Content-Length") or 0)
                data = json.loads(self.rfile.read(length) or b"{}")
            except Exception:
                return self._send_json(400, {"error": "Invalid JSON body"})
            name = str(data.get("name") or "").strip()
            category = str(data.get("category") or "electronics")
            try:
                base_price = float(data.get("basePriceUSD") or 0)
            except Exception:
                return self._send_json(400, {"error": "Invalid basePriceUSD"})
            specs = str(data.get("specs") or "").strip()
            image = str(data.get("image") or "").strip()
            if not name:
                return self._send_json(400, {"error": "Product name is required"})
            conn = get_db()
            cur = conn.execute(
                "INSERT INTO products (name, category, basePriceUSD, specs, image) VALUES (?,?,?,?,?)",
                (name, category, base_price, specs, image or "https://images.unsplash.com/photo-1526738549149-8e07eca6c147?w=600&auto=format&fit=crop&q=80"),
            )
            conn.commit()
            new_id = cur.lastrowid
            row = conn.execute(
                "SELECT id, name, category, basePriceUSD, specs, image FROM products WHERE id=?",
                (new_id,),
            ).fetchone()
            conn.close()
            return self._send_json(201, dict(row))
        return self._send_json(404, {"error": "Not Found"})

    def do_DELETE(self):
        parsed = urlparse(self.path)
        match = re.match(r"^/api/products/(\d+)$", parsed.path)
        if not match:
            return self._send_json(404, {"error": "Not Found"})
        if self.headers.get("X-Admin-Key") != ADMIN_KEY:
            return self._send_json(401, {"error": "Unauthorized"})
        conn = get_db()
        conn.execute("DELETE FROM products WHERE id=?", (int(match.group(1)),))
        conn.commit()
        conn.close()
        return self._send_json(200, {"status": "deleted"})


def run():
    os.chdir(PROJECT_ROOT)
    init_db()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), MarketSpaceHandler)
    print("MarketSpace Enterprise Core Systems backend running on http://localhost:%d" % PORT, flush=True)
    server.serve_forever()


if __name__ == "__main__":
    run()
