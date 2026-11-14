#!/usr/bin/env python3
"""Client for the official Blender MCP bridge.

The snippet must assign `result` to a JSON-serializable dict. Examples:

    blender_mcp.py 'import bpy\nresult = {"frame": bpy.context.scene.frame_current}'
    blender_mcp.py --file snippet.py
    blender_mcp.py < snippet.py
    blender_mcp.py --port 9876 --timeout 600 --file heavy_export.py

Exit codes: 0 ok, 1 Blender returned an error, 2 connection/usage failure.
"""

import argparse
import json
import socket
import sys


def call(code, host="127.0.0.1", port=9876, timeout=300):
    """Send one snippet to the bridge and return the decoded reply."""
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.sendall(
            (
                json.dumps({"type": "execute", "code": code, "strict_json": True})
                + "\0"
            ).encode("utf-8")
        )
        buf = b""
        while b"\0" not in buf:
            chunk = sock.recv(65536)
            if not chunk:
                break
            buf += chunk
    raw = buf.split(b"\0")[0]
    return json.loads(raw) if raw else {"status": "error", "message": "empty response"}


def build_parser():
    parser = argparse.ArgumentParser(
        description="Execute Python inside a running Blender through the official MCP add-on.",
        epilog="The snippet must set `result` to a JSON-serializable dict.",
    )
    parser.add_argument("code", nargs="?", help="Python snippet; omit to read stdin")
    parser.add_argument("-f", "--file", help="read the snippet from this file")
    parser.add_argument("--host", default="127.0.0.1", help="bridge host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=9876, help="bridge port (default: 9876)")
    parser.add_argument(
        "--timeout",
        type=float,
        default=300,
        help="socket timeout in seconds (default: 300; use 600+ for exports)",
    )
    parser.add_argument("--raw", action="store_true", help="print compact JSON")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.file:
        try:
            with open(args.file, encoding="utf-8") as handle:
                code = handle.read()
        except OSError as exc:
            print(json.dumps({"status": "error", "message": str(exc)}))
            return 2
    elif args.code is not None:
        code = args.code
    else:
        code = sys.stdin.read()

    if not code.strip():
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": "no code provided; pass a snippet, --file, or stdin",
                }
            )
        )
        return 2

    try:
        reply = call(code, host=args.host, port=args.port, timeout=args.timeout)
    except (OSError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": "%s: %s" % (type(exc).__name__, exc),
                    "hint": "Is Blender running with --online-mode? Run scripts/doctor.py.",
                }
            )
        )
        return 2

    print(json.dumps(reply, indent=None if args.raw else 1))
    return 0 if reply.get("status") == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
