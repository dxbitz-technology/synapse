"""Exercise the real renderers in headless Chrome at three viewport widths."""

import functools
import http.server
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

root = Path(__file__).resolve().parents[3]
chrome = (
	os.environ.get("CHROME_BIN")
	or shutil.which("google-chrome")
	or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
)
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{server.server_port}/apps/synapse/synapse/tests/browser.html"
try:
	for width in (1440, 800, 390):
		with tempfile.TemporaryDirectory(prefix="synapse-browser-") as profile:
			command = [
				chrome,
				"--headless",
				"--disable-gpu",
				"--no-sandbox",
				"--no-first-run",
				"--disable-background-networking",
				"--disable-component-update",
				"--disable-sync",
				"--no-default-browser-check",
				f"--user-data-dir={profile}",
				f"--window-size={width},800",
				"--virtual-time-budget=1500",
				"--dump-dom",
				url,
			]
			process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
			try:
				output, _ = process.communicate(timeout=30)
			except subprocess.TimeoutExpired:
				process.kill()
				output, _ = process.communicate()
			match = re.search(r'<pre id="results">(.*?)</pre>', output, re.S)
			if not match or 'data-complete="true"' not in output:
				raise SystemExit(f"Browser tests did not complete at {width}px")
			results = json.loads(match[1])
			failures = [item["name"] for item in results if not item["passed"]]
			if failures:
				raise SystemExit(f"Browser failures at {width}px: {failures}")
			print(f"{width}px: {len(results)} browser checks passed")
finally:
	server.shutdown()
