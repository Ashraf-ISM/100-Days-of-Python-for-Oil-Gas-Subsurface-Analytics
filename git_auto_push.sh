#!/usr/bin/env bash
# ==============================================================================
#  Git Auto Push (Production Edition)
#  Author: Md Ashraf
#  Description: Safe automated git add, commit, and push with validation
# ==============================================================================

set -Eeuo pipefail

# -----------------------------
# CONFIG
# -----------------------------
REMOTE="${1:-origin}"
BRANCH="$(git branch --show-current 2>/dev/null || echo main)"

# -----------------------------
# FUNCTIONS
# -----------------------------
log() { echo -e "[INFO] $*"; }
warn() { echo -e "[WARN] $*"; }
error() { echo -e "[ERROR] $*" >&2; }

check_git() {
    command -v git >/dev/null || { error "Git not installed"; exit 1; }
    git rev-parse --git-dir >/dev/null 2>&1 || {
        error "Not a git repository"
        exit 1
    }
}

check_changes() {
    if [[ -z "$(git status --porcelain)" ]]; then
        warn "No changes to commit"
        exit 0
    fi
}

suggest_commit() {
    files=$(git diff --cached --name-only)

    if echo "$files" | grep -q ".ipynb"; then
        echo "Add analysis notebook"
    elif echo "$files" | grep -q ".py"; then
        echo "Update Python module"
    else
        echo "Update project files"
    fi
}

# -----------------------------
# MAIN
# -----------------------------
check_git
check_changes

log "Staging changes..."
git add .

SUGGESTED=$(suggest_commit)
read -rp "Commit message [${SUGGESTED}]: " MSG
MSG="${MSG:-$SUGGESTED}"

if [[ ${#MSG} -lt 5 ]]; then
    error "Commit message too short"
    exit 1
fi

log "Committing..."
git commit -m "$MSG"

log "Pushing to $REMOTE/$BRANCH..."
git push "$REMOTE" "$BRANCH"

log "✔ Push successful"