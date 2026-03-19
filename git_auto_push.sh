#!/usr/bin/env bash
# ==============================================================================
#  Git Auto Push (Professional Edition)
#  Author: Md Ashraf
#  Description: Safe automated git add, commit, and push with retry logic
# ==============================================================================

set -Eeuo pipefail

# -----------------------------
# CONFIG
# -----------------------------
REMOTE="origin"
BRANCH="$(git branch --show-current 2>/dev/null || echo main)"
MAX_RETRIES=3

# -----------------------------
# LOGGING
# -----------------------------
log()   { echo -e "[INFO] $*"; }
warn()  { echo -e "[WARN] $*"; }
error() { echo -e "[ERROR] $*" >&2; }

# -----------------------------
# VALIDATION
# -----------------------------
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

# -----------------------------
# COMMIT MESSAGE SUGGESTION
# -----------------------------
suggest_commit() {
    files=$(git diff --cached --name-only)

    if echo "$files" | grep -qi "\.ipynb"; then
        echo "Add notebook for deep learning analysis"
    elif echo "$files" | grep -qi "\.py"; then
        echo "Update Python scripts"
    elif echo "$files" | grep -qi "fix\|bug"; then
        echo "Fix identified issues"
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

# Show status (important for debugging)
echo
git status --short
echo

# Commit message
SUGGESTED=$(suggest_commit)
read -rp "Commit message [${SUGGESTED}]: " MSG
MSG="${MSG:-$SUGGESTED}"

# Clean message (remove leading/trailing spaces)
MSG="$(echo "$MSG" | sed 's/^ *//;s/ *$//')"

if [[ ${#MSG} -lt 5 ]]; then
    error "Commit message too short"
    exit 1
fi

log "Committing..."
if ! git commit -m "$MSG"; then
    warn "Nothing to commit"
    exit 0
fi

# -----------------------------
# PUSH WITH RETRY (IMPORTANT)
# -----------------------------
log "Pushing to $REMOTE/$BRANCH..."

attempt=1
while [[ $attempt -le $MAX_RETRIES ]]; do
    if git push "$REMOTE" "$BRANCH"; then
        log "✔ Push successful"
        exit 0
    else
        warn "Push failed (attempt $attempt/$MAX_RETRIES)"
        sleep 2
    fi
    attempt=$((attempt + 1))
done

error "Push failed after $MAX_RETRIES attempts"

# Suggest recovery
echo
echo "Try manually:"
echo "  git pull --rebase $REMOTE $BRANCH"
echo "  git push $REMOTE $BRANCH"
exit 1