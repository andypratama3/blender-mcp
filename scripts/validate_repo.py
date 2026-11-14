#!/usr/bin/env python3
"""Validate the repository the way CI does. Standard library only.

    python3 scripts/validate_repo.py
    python3 scripts/validate_repo.py --quiet

Checks:
  1. Required files exist.
  2. Every skills/<name>/SKILL.md has valid frontmatter and name == folder.
  3. All Python files compile.
  4. No absolute paths containing a real username.
  5. No oversized files.
  6. Internal Markdown links resolve.

Exit code 0 when everything passes, 1 otherwise.
"""

import argparse
import ast
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REQUIRED = [
    "README.md",
    "README.id.md",
    "AGENTS.md",
    "CLAUDE.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "LICENSE",
    "CHANGELOG.md",
    "CITATION.cff",
    "Makefile",
    ".gitignore",
    "docs/AGENT_SETUP.md",
    "docs/INSTALL.md",
    "docs/MCP_BRIDGE.md",
    "docs/RIGGING_PLAYBOOK.md",
    "docs/VERIFICATION.md",
    "docs/RENDERING.md",
    "docs/TROUBLESHOOTING.md",
    "docs/SKILLS.md",
    "docs/ECOSYSTEM.md",
    "docs/CASE_STUDY_CRIMPING.md",
    "scripts/install.sh",
    "scripts/install.ps1",
    "scripts/doctor.py",
    "scripts/validate_repo.py",
    "skills/blender-live-rigging/SKILL.md",
]

SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", "vendor"}
MAX_BYTES = 512 * 1024

PERSONAL_PATH = re.compile(r"(?<![\w.-])/(?:Users|home)/([A-Za-z0-9._-]+)")
ALLOWED_USERS = {"you", "your", "user", "username", "example", "name"}
MD_LINK = re.compile(r"\[[^\]]*\]\(([^)\s#]+)(?:#[^)]*)?\)")


class Report:
    def __init__(self, quiet=False):
        self.quiet = quiet
        self.failures = []
        self.passes = 0

    def ok(self, message):
        self.passes += 1
        if not self.quiet:
            print("PASS %s" % message)

    def fail(self, message):
        self.failures.append(message)
        print("FAIL %s" % message)


def walk_files():
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(files):
            yield os.path.join(base, name)


def parse_frontmatter(text):
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    block = text[3:end].strip("\n")
    data = {}
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            return None
        key, value = line.split(":", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        data[key.strip()] = value
    return data


def check_required(report):
    for rel in REQUIRED:
        path = os.path.join(ROOT, rel)
        if os.path.isfile(path):
            report.ok("required %s" % rel)
        else:
            report.fail("missing required file %s" % rel)


def check_skills(report):
    skills_dir = os.path.join(ROOT, "skills")
    if not os.path.isdir(skills_dir):
        report.fail("skills/ directory missing")
        return
    for name in sorted(os.listdir(skills_dir)):
        folder = os.path.join(skills_dir, name)
        if not os.path.isdir(folder):
            continue
        skill = os.path.join(folder, "SKILL.md")
        if not os.path.isfile(skill):
            report.fail("skills/%s has no SKILL.md" % name)
            continue
        with open(skill, encoding="utf-8") as handle:
            text = handle.read()
        meta = parse_frontmatter(text)
        if meta is None:
            report.fail("skills/%s/SKILL.md frontmatter is missing or malformed" % name)
            continue
        if meta.get("name") != name:
            report.fail(
                "skills/%s/SKILL.md name '%s' does not match folder"
                % (name, meta.get("name"))
            )
        else:
            report.ok("skill name %s" % name)
        description = meta.get("description", "")
        if not 20 <= len(description) <= 1024:
            report.fail(
                "skills/%s/SKILL.md description length %d (need 20-1024)"
                % (name, len(description))
            )
        else:
            report.ok("skill description %s (%d chars)" % (name, len(description)))
        if "# " not in text.split("---", 2)[-1]:
            report.fail("skills/%s/SKILL.md has no H1 heading" % name)


def check_python(report):
    for path in walk_files():
        if not path.endswith(".py"):
            continue
        rel = os.path.relpath(path, ROOT)
        with open(path, encoding="utf-8") as handle:
            source = handle.read()
        try:
            ast.parse(source, filename=rel)
        except SyntaxError as exc:
            report.fail("%s syntax error: %s" % (rel, exc))
        else:
            report.ok("python %s" % rel)


def check_paths(report):
    for path in walk_files():
        rel = os.path.relpath(path, ROOT)
        if path.endswith((".png", ".jpg", ".jpeg", ".glb", ".blend")):
            continue
        try:
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
        except (UnicodeDecodeError, OSError):
            continue
        for match in PERSONAL_PATH.finditer(text):
            user = match.group(1)
            if user.lower() not in ALLOWED_USERS:
                report.fail("%s contains a personal path: %s" % (rel, match.group(0)))
                break
        else:
            report.ok("paths %s" % rel)


def check_sizes(report):
    for path in walk_files():
        rel = os.path.relpath(path, ROOT)
        size = os.path.getsize(path)
        if size > MAX_BYTES:
            report.fail("%s is %d bytes (limit %d)" % (rel, size, MAX_BYTES))
        elif path.endswith(".md"):
            report.ok("size %s" % rel)


def check_links(report):
    for path in walk_files():
        if not path.endswith(".md"):
            continue
        rel = os.path.relpath(path, ROOT)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        broken = []
        for target in MD_LINK.findall(text):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            candidate = os.path.normpath(os.path.join(os.path.dirname(path), target))
            if not os.path.exists(candidate):
                broken.append(target)
        if broken:
            report.fail("%s has broken links: %s" % (rel, ", ".join(broken)))
        else:
            report.ok("links %s" % rel)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate the repository.")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    report = Report(quiet=args.quiet)
    check_required(report)
    check_skills(report)
    check_python(report)
    check_paths(report)
    check_sizes(report)
    check_links(report)

    print("")
    if report.failures:
        print("%d FAIL / %d PASS" % (len(report.failures), report.passes))
        return 1
    print("0 FAIL / %d PASS" % report.passes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
