"""
转盘后端服务 — 零依赖，纯标准库
运行: python server.py
访问: http://localhost:8080
"""

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote

BASE_DIR  = Path(__file__).parent
DATA_FILE = BASE_DIR / "items.json"
HTML_FILE = BASE_DIR / "wheel.html"
PORT      = 8080


# ── 数据层 ─────────────────────────────────────────────────

def load_items() -> list[str]:
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []

def save_items(items: list[str]) -> None:
    DATA_FILE.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


# ── HTTP 处理 ──────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):

    # 屏蔽访问日志，保持终端干净（错误仍会打印）
    def log_message(self, fmt, *args):
        pass

    # ── GET ──
    def do_GET(self):
        if self.path == "/":
            self._serve_file(HTML_FILE, "text/html; charset=utf-8")
        elif self.path == "/api/items":
            self._json(200, load_items())
        else:
            self._text(404, "Not Found")

    # ── POST /api/items  body: {"item": "xxx"} ──
    def do_POST(self):
        if self.path != "/api/items":
            self._text(404, "Not Found")
            return
        body = self._read_body()
        if body is None:
            return
        item = body.get("item", "").strip()
        if not item:
            self._json(400, {"error": "item 不能为空"})
            return
        items = load_items()
        if item in items:
            self._json(409, {"error": "选项已存在"})
            return
        items.append(item)
        save_items(items)
        self._json(200, items)

    # ── DELETE /api/items  body: {"item": "xxx"} ──
    def do_DELETE(self):
        if self.path != "/api/items":
            self._text(404, "Not Found")
            return
        body = self._read_body()
        if body is None:
            return
        item = body.get("item", "").strip()
        if not item:
            self._json(400, {"error": "item 不能为空"})
            return
        items = load_items()
        if item not in items:
            self._json(404, {"error": "选项不存在"})
            return
        items.remove(item)
        save_items(items)
        self._json(200, items)

    # ── PUT /api/items  body: {"items": [...]} 批量保存 ──
    def do_PUT(self):
        if self.path != "/api/items":
            self._text(404, "Not Found")
            return
        body = self._read_body()
        if body is None:
            return
        new_items = body.get("items")
        if not isinstance(new_items, list):
            self._json(400, {"error": "需要 items 数组"})
            return
        new_items = [str(x).strip() for x in new_items if str(x).strip()]
        save_items(new_items)
        self._json(200, new_items)

    # ── 工具方法 ──────────────────────────────────────────

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            self._json(400, {"error": "JSON 解析失败"})
            return None
        return data

    def _json(self, code: int, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _text(self, code: int, msg: str):
        body = msg.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, path: Path, ctype: str):
        try:
            body = path.read_bytes()
        except FileNotFoundError:
            self._text(404, "文件未找到")
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()


# ── 启动 ───────────────────────────────────────────────────

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"转盘服务已启动 → http://localhost:{PORT}")
    print(f"数据文件: {DATA_FILE}")
    print("按 Ctrl+C 停止\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
