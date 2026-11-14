#!/usr/bin/env python3
"""Check the Blender MCP environment: Blender, add-on, port, bridge, skill, Python.

    python3 scripts/doctor.py
    python3 scripts/doctor.py --json
    python3 scripts/doctor.py --blender "/Applications/Blender.app/Contents/MacOS/Blender"

Exit codes: 0 all checks pass, 1 at least one check failed, 2 usage error.
Standard library only; works on macOS, Linux, and Windows.
"""

import argparse
import glob
import json
import os
import platform
import socket
import subprocess
import sys

SKILL_NAME = "blender-live-rigging"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9876

STATUS_ORDER = {"PASS": 0, "WARN": 1, "FAIL": 2}


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def candidate_blender_paths():
    system = platform.system()
    if system == "Darwin":
        return [
            "/Applications/Blender.app/Contents/MacOS/Blender",
            os.path.expanduser("~/Applications/Blender.app/Contents/MacOS/Blender"),
        ]
    if system == "Windows":
        roots = [
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        ]
        found = []
        for root in filter(None, roots):
            found.extend(glob.glob(os.path.join(root, "Blender Foundation", "Blender*", "blender.exe")))
        return found
    return ["/usr/bin/blender", "/usr/local/bin/blender", "/snap/bin/blender"]


def find_blender(explicit=None):
    if explicit:
        return explicit if os.path.isfile(explicit) else None
    which = None
    for name in ("blender", "blender.exe"):
        for base in os.environ.get("PATH", "").split(os.pathsep):
            candidate = os.path.join(base, name)
            if os.path.isfile(candidate):
                which = candidate
                break
        if which:
            break
    if which:
        return which
    for candidate in candidate_blender_paths():
        if os.path.isfile(candidate):
            return candidate
    return None


def blender_version(path):
    try:
        proc = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return None, "%s: %s" % (type(exc).__name__, exc)
    first = (proc.stdout or proc.stderr).strip().splitlines()
    return (first[0].replace("Blender ", "").strip() if first else None), None


def extension_roots():
    system = platform.system()
    home = os.path.expanduser("~")
    if system == "Darwin":
        bases = [os.path.join(home, "Library", "Application Support", "Blender")]
    elif system == "Windows":
        appdata = os.environ.get("APPDATA", os.path.join(home, "AppData", "Roaming"))
        bases = [os.path.join(appdata, "Blender Foundation", "Blender")]
    else:
        bases = [
            os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.join(home, ".config")), "blender"),
        ]
    override = os.environ.get("BLENDER_USER_EXTENSIONS")
    if override:
        bases.append(os.path.dirname(override))
    roots = []
    for base in bases:
        roots.extend(glob.glob(os.path.join(base, "*", "extensions")))
        roots.extend(glob.glob(os.path.join(base, "extensions")))
    return roots


def find_addon():
    matches = []
    for root in extension_roots():
        path = os.path.join(root, "blenderlab", "mcp")
        if os.path.isdir(path):
            matches.append(path)
        if os.path.isdir(os.path.join(path, "bl_ext")):
            matches.append(os.path.join(path, "bl_ext"))
    return matches


def port_listening(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(2.0)
        return sock.connect_ex((host, port)) == 0


def bridge_call(host, port, timeout=15.0):
    code = (
        "import bpy\n"
        "result = {'gui': not bpy.app.background, "
        "'version': bpy.app.version_string, 'file': bpy.data.filepath, "
        "'objects': len(bpy.data.objects)}"
    )
    payload = json.dumps({"type": "execute", "code": code, "strict_json": True}) + "\0"
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.sendall(payload.encode("utf-8"))
        buf = b""
        while b"\0" not in buf:
            chunk = sock.recv(65536)
            if not chunk:
                break
            buf += chunk
    raw = buf.split(b"\0")[0]
    if not raw:
        return {"status": "error", "message": "empty response"}
    return json.loads(raw)


def skill_locations():
    home = os.path.expanduser("~")
    xdg = os.environ.get("XDG_CONFIG_HOME", os.path.join(home, ".config"))
    return [
        os.path.join(xdg, "opencode", "skills", SKILL_NAME),
        os.path.join(home, ".claude", "skills", SKILL_NAME),
        os.path.join(home, ".agents", "skills", SKILL_NAME),
        os.path.join(home, ".cursor", "skills", SKILL_NAME),
    ]


def check_skill():
    installed = [path for path in skill_locations() if os.path.exists(path)]
    repo_copy = os.path.join(repo_root(), "skills", SKILL_NAME)
    detail = {"installed": installed, "repo_copy": repo_copy}
    if installed:
        return "PASS", detail
    return "WARN", detail


def collect(blender_path, host, port):
    checks = []

    if blender_path:
        version, error = blender_version(blender_path)
        if version:
            checks.append(("Blender", "PASS", "%s (%s)" % (version, blender_path)))
        else:
            checks.append(("Blender", "WARN", "found but --version failed: %s" % error))
    else:
        checks.append(("Blender", "FAIL", "not found; install 5.2+ or pass --blender"))

    addons = find_addon()
    if addons:
        checks.append(("MCP add-on", "PASS", addons[0]))
    else:
        checks.append(
            ("MCP add-on", "FAIL", "bl_ext.blenderlab.mcp not found in extension dirs")
        )

    listening = port_listening(host, port)
    if listening:
        checks.append(("Port %d" % port, "PASS", "listening on %s" % host))
    else:
        checks.append(
            ("Port %d" % port, "FAIL", "closed; launch Blender with --online-mode")
        )

    if listening:
        try:
            reply = bridge_call(host, port)
        except (OSError, ValueError) as exc:
            checks.append(("Bridge", "FAIL", "%s: %s" % (type(exc).__name__, exc)))
        else:
            if reply.get("status") == "ok":
                data = reply.get("result", {})
                checks.append(
                    (
                        "Bridge",
                        "PASS",
                        "gui=%s version=%s file=%s"
                        % (
                            "true" if data.get("gui") else "false",
                            data.get("version"),
                            data.get("file") or "<unsaved>",
                        ),
                    )
                )
            else:
                checks.append(("Bridge", "FAIL", reply.get("message", "unknown error")))
    else:
        checks.append(("Bridge", "FAIL", "skipped: port closed"))

    status, detail = check_skill()
    checks.append(
        (
            "Skill",
            status,
            detail["installed"][0] if detail["installed"] else "not installed; run scripts/install.sh --agent <agent>",
        )
    )

    py = platform.python_version()
    checks.append(("Python", "PASS" if sys.version_info >= (3, 10) else "FAIL", py))
    return checks


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Check Blender, the official MCP add-on, the bridge, and the installed skill."
    )
    parser.add_argument("--blender", help="path to the Blender executable")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    blender_path = find_blender(args.blender)
    checks = collect(blender_path, args.host, args.port)

    counts = {"PASS": 0, "WARN": 0, "FAIL": 0}
    for _, status, _ in checks:
        counts[status] += 1
    worst = max(STATUS_ORDER[status] for _, status, _ in checks)

    if args.json:
        print(
            json.dumps(
                {
                    "checks": [
                        {"name": name, "status": status, "detail": detail}
                        for name, status, detail in checks
                    ],
                    "summary": counts,
                    "blender": blender_path,
                    "host": args.host,
                    "port": args.port,
                },
                indent=2,
            )
        )
    else:
        width = max(len(name) for name, _, _ in checks) + 2
        for name, status, detail in checks:
            print("%-*s%-6s%s" % (width, name, status, detail))
        print(
            "%d PASS / %d WARN / %d FAIL"
            % (counts["PASS"], counts["WARN"], counts["FAIL"])
        )

    return 0 if worst == 0 else (1 if worst == 2 else 1)


if __name__ == "__main__":
    sys.exit(main())
