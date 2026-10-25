#!/usr/bin/env python3
"""Minimal web interface to edit berryconfig.py and restart the BerryMetre visualization.

Uses only the Python standard library so it runs with the system python3.

    python3 berrywebconfig.py --config ../berryconfig.py --start-script ~/startBerryMetre.sh --port 8080
"""

import argparse
import ast
import html
import os
import shutil
import subprocess
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CLASS_NAME = "BerryConfiguration"
RECEIVER_PATTERN = r"python.*BerryMetrePythonReceiver\.py"  # pgrep/pkill pattern of the visualization
CHOICES = {
    "mode": ["serial", "udp"],
    "printerType": ["brother", "peripage"],
}

args = None


def read_config():
    """Return the config source lines and a list of fields found in the BerryConfiguration class."""
    with open(args.config) as f:
        source = f.read()
    lines = source.splitlines()
    tree = ast.parse(source)
    fields = []
    for node in tree.body:
        if not (isinstance(node, ast.ClassDef) and node.name == CLASS_NAME):
            continue
        for item in node.body:
            if not (isinstance(item, ast.Assign) and len(item.targets) == 1 and isinstance(item.targets[0], ast.Name)):
                continue
            try:
                value = ast.literal_eval(item.value)
            except ValueError:
                continue  # not a plain literal, leave it alone
            rest = lines[item.end_lineno - 1][item.end_col_offset:].strip()
            fields.append({
                "name": item.targets[0].id,
                "value": value,
                "comment": rest[1:].strip() if rest.startswith("#") else "",
                "lineno": item.lineno,
                "end_lineno": item.end_lineno,
                "indent": lines[item.lineno - 1][:item.col_offset],
            })
    return lines, fields


def parse_value(field, form):
    """Convert the submitted form value back to the type of the current value."""
    name, old = field["name"], field["value"]
    if isinstance(old, bool):
        return name in form
    raw = form.get(name, [""])[0].strip()
    if isinstance(old, int):
        return int(raw)
    if isinstance(old, float):
        return float(raw)
    if isinstance(old, str):
        return raw
    value = ast.literal_eval(raw)
    if type(value) is not type(old):
        raise ValueError(f"expected {type(old).__name__}")
    return value


def write_config(form):
    lines, fields = read_config()
    errors = []
    # Replace from the bottom so line numbers of earlier fields stay valid
    for field in sorted(fields, key=lambda f: f["lineno"], reverse=True):
        try:
            value = parse_value(field, form)
        except (ValueError, SyntaxError) as e:
            errors.append(f"{field['name']}: {e}")
            continue
        if value == field["value"] and type(value) is type(field["value"]):
            continue
        line = f"{field['indent']}{field['name']} = {value!r}"
        if field["comment"]:
            line = f"{line:<48}# {field['comment']}"
        lines[field["lineno"] - 1:field["end_lineno"]] = [line]
    if errors:
        return errors
    new_source = "\n".join(lines) + "\n"
    compile(new_source, args.config, "exec")
    shutil.copy2(args.config, args.config + ".bak")
    tmp = args.config + ".tmp"
    with open(tmp, "w") as f:
        f.write(new_source)
    os.replace(tmp, args.config)
    return []


def visualization_running():
    return subprocess.run(["pgrep", "-f", RECEIVER_PATTERN], capture_output=True).returncode == 0


def restart_visualization():
    subprocess.run(["pkill", "-f", RECEIVER_PATTERN])
    for _ in range(50):
        if not visualization_running():
            break
        time.sleep(0.1)
    else:
        subprocess.run(["pkill", "-KILL", "-f", RECEIVER_PATTERN])
    env = dict(os.environ)
    env.setdefault("DISPLAY", ":0")
    env.setdefault("XAUTHORITY", os.path.expanduser("~/.Xauthority"))
    # setsid -f detaches the script so it is not a child of this server
    subprocess.run(["setsid", "-f", "bash", args.start_script], env=env,
                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def log_tail(n=30):
    try:
        with open(args.log, errors="replace") as f:
            return "".join(f.readlines()[-n:])
    except OSError as e:
        return str(e)


def field_input(field):
    name, value = field["name"], field["value"]
    esc = html.escape
    if isinstance(value, bool):
        checked = " checked" if value else ""
        return f'<input type="checkbox" name="{esc(name)}" id="{esc(name)}"{checked}>'
    if name in CHOICES:
        options = CHOICES[name] if value in CHOICES[name] else [value] + CHOICES[name]
        opts = "".join(f'<option{" selected" if o == value else ""}>{esc(o)}</option>' for o in options)
        return f'<select name="{esc(name)}" id="{esc(name)}">{opts}</select>'
    if isinstance(value, int):
        return f'<input type="number" step="1" name="{esc(name)}" id="{esc(name)}" value="{value}">'
    if isinstance(value, float):
        return f'<input type="number" step="any" name="{esc(name)}" id="{esc(name)}" value="{value!r}">'
    if isinstance(value, str):
        return f'<input type="text" name="{esc(name)}" id="{esc(name)}" value="{esc(value)}">'
    return f'<input type="text" name="{esc(name)}" id="{esc(name)}" value="{esc(repr(value))}">'


def render_page(message="", error=False):
    try:
        _, fields = read_config()
        load_error = ""
    except (OSError, SyntaxError) as e:
        fields, load_error = [], f"Cannot read {args.config}: {e}"
    rows = "".join(
        f'<tr><td><label for="{html.escape(f["name"])}">{html.escape(f["name"])}</label></td>'
        f'<td>{field_input(f)}</td><td class="c">{html.escape(f["comment"])}</td></tr>'
        for f in fields
    )
    running = visualization_running()
    status = '<span class="ok">running</span>' if running else '<span class="bad">not running</span>'
    msg = ""
    if load_error or message:
        msg = f'<p class="{"bad" if error or load_error else "ok"}">{html.escape(load_error or message)}</p>'
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>BerryMetre Configuration</title>
<style>
body {{ font-family: sans-serif; margin: 1em; background: #fafafa; color: #222; }}
h1 {{ color: #8b1a3a; font-size: 1.4em; }}
table {{ border-collapse: collapse; width: 100%; }}
td {{ padding: 4px 6px; border-bottom: 1px solid #ddd; vertical-align: middle; }}
td.c {{ color: #666; font-size: 0.85em; }}
input[type=text], input[type=number], select {{ width: 100%; box-sizing: border-box; padding: 4px; }}
button {{ padding: 8px 14px; margin: 8px 8px 8px 0; font-size: 1em; }}
.ok {{ color: #1a7f37; font-weight: bold; }}
.bad {{ color: #c62828; font-weight: bold; }}
pre {{ background: #222; color: #ddd; padding: 8px; overflow-x: auto; font-size: 0.8em; }}
</style></head><body>
<h1>BerryMetre Configuration</h1>
{msg}
<p>Visualization: {status} &nbsp; <small>{html.escape(args.config)}</small></p>
<form method="post" action="/restart"><button type="submit">Restart visualization</button></form>
<form method="post" action="/save">
<table>{rows}</table>
<button type="submit" name="action" value="save">Save</button>
<button type="submit" name="action" value="save_restart">Save &amp; restart visualization</button>
</form>
<h2>Log ({html.escape(args.log)})</h2>
<pre>{html.escape(log_tail())}</pre>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def send_html(self, body, status=200):
        data = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def redirect(self, message, error=False):
        query = urllib.parse.urlencode({"msg": message, "err": "1" if error else ""})
        self.send_response(303)
        self.send_header("Location", "/?" + query)
        self.end_headers()

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if url.path != "/":
            self.send_error(404)
            return
        query = urllib.parse.parse_qs(url.query)
        self.send_html(render_page(query.get("msg", [""])[0], bool(query.get("err", [""])[0])))

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        form = urllib.parse.parse_qs(self.rfile.read(length).decode(), keep_blank_values=True)
        if self.path == "/restart":
            restart_visualization()
            self.redirect("Visualization restarted.")
        elif self.path == "/save":
            try:
                errors = write_config(form)
            except (OSError, SyntaxError) as e:
                errors = [str(e)]
            if errors:
                self.redirect("Not saved: " + "; ".join(errors), error=True)
            elif form.get("action", [""])[0] == "save_restart":
                restart_visualization()
                self.redirect("Configuration saved, visualization restarted.")
            else:
                self.redirect("Configuration saved. Restart the visualization to apply it.")
        else:
            self.send_error(404)


def main():
    global args
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default=os.path.join(here, "..", "berryconfig.py"))
    parser.add_argument("--start-script", default=os.path.expanduser("~/startBerryMetre.sh"))
    parser.add_argument("--log", default=None, help="log file to show (default: berrymetre.log next to the config)")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    args.config = os.path.abspath(os.path.expanduser(args.config))
    args.log = args.log or os.path.join(os.path.dirname(args.config), "berrymetre.log")
    print(f"Serving on http://{args.host}:{args.port}/ editing {args.config}", flush=True)
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
