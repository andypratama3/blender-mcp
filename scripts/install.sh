#!/usr/bin/env bash
# Install the blender-live-rigging skill for one or more agent harnesses.
#
#   ./scripts/install.sh --agent opencode
#   ./scripts/install.sh --agent all
#   ./scripts/install.sh --agent claude --copy
#   ./scripts/install.sh --agent opencode --scope project --project ~/my-repo
#   ./scripts/install.sh --agent opencode --uninstall
#
# Symlink by default on macOS/Linux. Only ever manages the skill named below.

set -euo pipefail

SKILL_NAME="blender-live-rigging"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
SRC="$REPO_ROOT/skills/$SKILL_NAME"

AGENT=""
SCOPE="user"
PROJECT=""
MODE="link"
UNINSTALL=0
FORCE=0

die() { printf 'error: %s\n' "$*" >&2; exit 1; }
info() { printf '%s\n' "$*"; }

usage() {
  cat <<'EOF'
Usage: install.sh --agent <name> [options]

Agents:
  opencode   ~/.config/opencode/skills
  claude     ~/.claude/skills
  agents     ~/.agents/skills
  codex      ~/.agents/skills
  gemini     ~/.agents/skills
  copilot    ~/.agents/skills
  cursor     ~/.cursor/skills
  all        every directory above

Options:
  --agent NAME        target harness (required unless --uninstall with --agent all)
  --scope user|project
  --project DIR       project root when --scope project
  --copy              copy instead of symlink (Windows-like behavior)
  --uninstall         remove the skill from the target(s)
  --force             replace a foreign directory with the same name
  -h, --help          show this help
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --agent) AGENT="${2:-}"; shift 2 ;;
    --agent=*) AGENT="${1#*=}"; shift ;;
    --scope) SCOPE="${2:-}"; shift 2 ;;
    --scope=*) SCOPE="${1#*=}"; shift ;;
    --project) PROJECT="${2:-}"; shift 2 ;;
    --project=*) PROJECT="${1#*=}"; shift ;;
    --copy) MODE="copy"; shift ;;
    --uninstall) UNINSTALL=1; shift ;;
    --force) FORCE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1 (try --help)" ;;
  esac
done

[ -n "$AGENT" ] || die "--agent is required (try --help)"
[ -d "$SRC" ] || die "skill source missing: $SRC"

case "$SCOPE" in
  user) ;;
  project)
    [ -n "$PROJECT" ] || die "--scope project requires --project DIR"
    [ -d "$PROJECT" ] || die "project directory not found: $PROJECT"
    PROJECT="$(cd -- "$PROJECT" && pwd)"
    ;;
  *) die "--scope must be user or project" ;;
esac

targets_for() {
  case "$1" in
    opencode) printf '%s\n' "opencode" ;;
    claude)   printf '%s\n' "claude" ;;
    agents|codex|gemini|copilot) printf '%s\n' "agents" ;;
    cursor)   printf '%s\n' "cursor" ;;
    all)      printf '%s\n' opencode claude agents cursor ;;
    *) die "unknown agent: $1 (try --help)" ;;
  esac
}

dir_for() {
  if [ "$SCOPE" = "project" ]; then
    case "$1" in
      opencode) printf '%s\n' "$PROJECT/.opencode/skills" ;;
      claude)   printf '%s\n' "$PROJECT/.claude/skills" ;;
      agents)   printf '%s\n' "$PROJECT/.agents/skills" ;;
      cursor)   printf '%s\n' "$PROJECT/.cursor/skills" ;;
    esac
    return
  fi
  case "$1" in
    opencode) printf '%s\n' "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills" ;;
    claude)   printf '%s\n' "$HOME/.claude/skills" ;;
    agents)   printf '%s\n' "$HOME/.agents/skills" ;;
    cursor)   printf '%s\n' "$HOME/.cursor/skills" ;;
  esac
}

install_one() {
  local name="$1" dir dest
  dir="$(dir_for "$name")"
  [ -n "$dir" ] || die "no install dir for $name"
  dest="$dir/$SKILL_NAME"
  mkdir -p "$dir"

  if [ -L "$dest" ]; then
    local current
    current="$(readlink "$dest" || true)"
    if [ "$current" = "$SRC" ]; then
      info "ok       $dest already points at this repo ($name)"
      return
    fi
    rm -- "$dest"
  elif [ -e "$dest" ]; then
    if [ "$FORCE" -ne 1 ]; then
      die "$dest exists and is not a symlink from this repo; inspect it or re-run with --force"
    fi
    rm -rf -- "$dest"
  fi

  if [ "$MODE" = "copy" ]; then
    cp -R -- "$SRC" "$dest"
    info "installed $SKILL_NAME -> $dir ($name, copy)"
  else
    ln -s -- "$SRC" "$dest"
    info "installed $SKILL_NAME -> $dir ($name, symlink)"
  fi
}

uninstall_one() {
  local name="$1" dir dest
  dir="$(dir_for "$name")"
  dest="$dir/$SKILL_NAME"
  if [ -L "$dest" ] || [ -e "$dest" ]; then
    rm -rf -- "$dest"
    info "removed   $dest ($name)"
  else
    info "absent    $dest ($name)"
  fi
}

for target in $(targets_for "$AGENT"); do
  if [ "$UNINSTALL" -eq 1 ]; then
    uninstall_one "$target"
  else
    install_one "$target"
  fi
done

if [ "$UNINSTALL" -eq 0 ]; then
  info ""
  info "next: python3 \"$REPO_ROOT/scripts/doctor.py\""
fi
