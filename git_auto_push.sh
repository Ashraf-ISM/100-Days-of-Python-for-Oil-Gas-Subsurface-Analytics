#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║              G I T   A U T O P U S H   —   P R O   E D I T I O N           ║
# ║                         Author : Md Ashraf                                  ║
# ║           Safe automated git add · commit · push with retry logic           ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

set -Eeuo pipefail

# ──────────────────────────────────────────────────────────────────────────────
#  TRUE-COLOR PALETTE
# ──────────────────────────────────────────────────────────────────────────────
ESC=$'\033'
RESET="${ESC}[0m"
BOLD="${ESC}[1m"
DIM="${ESC}[2m"
ITALIC="${ESC}[3m"

# Foreground
FG_WHITE="${ESC}[97m"
FG_NAVY="${ESC}[38;2;30;90;160m"
FG_AMBER="${ESC}[38;2;255;180;0m"
FG_GREEN="${ESC}[38;2;80;220;120m"
FG_RED="${ESC}[38;2;255;80;80m"
FG_CYAN="${ESC}[38;2;80;220;240m"
FG_MAGENTA="${ESC}[38;2;200;100;240m"
FG_GRAY="${ESC}[38;2;140;150;165m"
FG_ORANGE="${ESC}[38;2;255;130;50m"

# Background accents
BG_NAVY="${ESC}[48;2;10;25;60m"
BG_DARK="${ESC}[48;2;12;14;20m"
BG_AMBER="${ESC}[48;2;255;180;0m"
BG_GREEN="${ESC}[48;2;20;80;40m"
BG_RED="${ESC}[48;2;80;20;20m"

# ──────────────────────────────────────────────────────────────────────────────
#  CONFIG
# ──────────────────────────────────────────────────────────────────────────────
REMOTE="origin"
BRANCH="$(git branch --show-current 2>/dev/null || echo main)"
MAX_RETRIES=3

# ──────────────────────────────────────────────────────────────────────────────
#  BANNER
# ──────────────────────────────────────────────────────────────────────────────
print_banner() {
    echo
    echo -e "${BG_NAVY}${FG_AMBER}${BOLD}"
    echo -e "  ╔══════════════════════════════════════════════════════════╗  "
    echo -e "  ║   ⬡  GIT AUTOPUSH  ·  PRO EDITION                      ║  "
    echo -e "  ║   ─────────────────────────────────────────────────     ║  "
    echo -e "  ║   ${FG_CYAN}Branch${FG_AMBER} › ${FG_WHITE}${BRANCH}${FG_AMBER}   ${FG_CYAN}Remote${FG_AMBER} › ${FG_WHITE}${REMOTE}${FG_AMBER}                        ║  "
    echo -e "  ║   ${FG_GRAY}Author${FG_AMBER} · Md Ashraf                                   ║  "
    echo -e "  ╚══════════════════════════════════════════════════════════╝  "
    echo -e "${RESET}"
}

# ──────────────────────────────────────────────────────────────────────────────
#  SECTION HEADER
# ──────────────────────────────────────────────────────────────────────────────
section() {
    local icon="$1"; local title="$2"
    echo
    echo -e "${FG_NAVY}${BOLD}  ┌─${RESET} ${icon}  ${BOLD}${FG_WHITE}${title}${RESET}  ${FG_NAVY}──────────────────────────────────${RESET}"
}

# ──────────────────────────────────────────────────────────────────────────────
#  LOGGING
# ──────────────────────────────────────────────────────────────────────────────
log()     { echo -e "  ${FG_GREEN}${BOLD}✔${RESET}  ${FG_WHITE}$*${RESET}"; }
info()    { echo -e "  ${FG_CYAN}${BOLD}◆${RESET}  ${FG_WHITE}$*${RESET}"; }
warn()    { echo -e "  ${FG_AMBER}${BOLD}▲${RESET}  ${FG_AMBER}$*${RESET}"; }
error()   { echo -e "  ${FG_RED}${BOLD}✖${RESET}  ${BG_RED}${FG_WHITE} ERROR ${RESET}  ${FG_RED}$*${RESET}" >&2; }
dim_msg() { echo -e "  ${FG_GRAY}${DIM}  $*${RESET}"; }

# ──────────────────────────────────────────────────────────────────────────────
#  SPINNER
# ──────────────────────────────────────────────────────────────────────────────
_SPIN_PID=""
spinner_start() {
    local msg="${1:-Working...}"
    local frames=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")
    (
        local i=0
        while true; do
            printf "\r  ${FG_CYAN}${BOLD}%s${RESET}  ${FG_WHITE}%s${RESET} " "${frames[$((i % 10))]}" "$msg"
            sleep 0.08
            i=$((i + 1))
        done
    ) &
    _SPIN_PID=$!
}

spinner_stop() {
    if [[ -n "$_SPIN_PID" ]]; then
        kill "$_SPIN_PID" 2>/dev/null
        wait "$_SPIN_PID" 2>/dev/null || true
        _SPIN_PID=""
        printf "\r\033[2K"   # clear line
    fi
}

# ──────────────────────────────────────────────────────────────────────────────
#  PROGRESS BAR
# ──────────────────────────────────────────────────────────────────────────────
progress_bar() {
    local current="$1"; local total="$2"; local label="${3:-}"
    local width=40
    local filled=$(( current * width / total ))
    local empty=$(( width - filled ))
    local bar=""
    for ((i=0; i<filled; i++)); do bar+="█"; done
    for ((i=0; i<empty; i++));  do bar+="░"; done
    local pct=$(( current * 100 / total ))
    printf "  ${FG_NAVY}[${FG_AMBER}${BOLD}%s${RESET}${FG_NAVY}]${RESET}  ${FG_WHITE}${BOLD}%3d%%${RESET}  ${FG_GRAY}%s${RESET}\n" \
        "$bar" "$pct" "$label"
}

# ──────────────────────────────────────────────────────────────────────────────
#  HORIZONTAL RULE
# ──────────────────────────────────────────────────────────────────────────────
hr() {
    echo -e "  ${FG_NAVY}${DIM}────────────────────────────────────────────────────────${RESET}"
}

# ──────────────────────────────────────────────────────────────────────────────
#  VALIDATION
# ──────────────────────────────────────────────────────────────────────────────
check_git() {
    section "🔎" "ENVIRONMENT CHECK"
    spinner_start "Verifying git installation..."
    sleep 0.4
    spinner_stop
    command -v git >/dev/null || { error "Git not found in PATH"; exit 1; }
    log "Git binary found  $(git --version)"

    spinner_start "Checking repository context..."
    sleep 0.3
    spinner_stop
    git rev-parse --git-dir >/dev/null 2>&1 || {
        error "Not inside a git repository"
        exit 1
    }
    log "Repository detected"
    dim_msg "$(git rev-parse --show-toplevel)"
}

check_changes() {
    section "📂" "WORKING TREE"
    local status
    status="$(git status --porcelain)"
    if [[ -z "$status" ]]; then
        warn "Working tree is clean — nothing to commit"
        hr
        exit 0
    fi

    # Count changed files
    local n_added n_modified n_deleted
    n_added=$(echo "$status"   | grep -c "^A\|^??"   || true)
    n_modified=$(echo "$status"| grep -c "^M\| M"    || true)
    n_deleted=$(echo "$status" | grep -c "^D\| D"    || true)

    echo
    echo -e "  ${FG_GREEN}${BOLD}+${RESET} ${FG_WHITE}New / Untracked   ${FG_GREEN}${BOLD}${n_added}${RESET}"
    echo -e "  ${FG_AMBER}${BOLD}~${RESET} ${FG_WHITE}Modified          ${FG_AMBER}${BOLD}${n_modified}${RESET}"
    echo -e "  ${FG_RED}${BOLD}−${RESET} ${FG_WHITE}Deleted           ${FG_RED}${BOLD}${n_deleted}${RESET}"
    echo
    git status --short | sed "s/^/  ${FG_GRAY}  /;s/$/${RESET}/"
}

# ──────────────────────────────────────────────────────────────────────────────
#  SMART COMMIT SUGGESTION
# ──────────────────────────────────────────────────────────────────────────────
suggest_commit() {
    local files
    files="$(git diff --cached --name-only 2>/dev/null)"
    [[ -z "$files" ]] && files="$(git status --porcelain | awk '{print $2}')"

    if   echo "$files" | grep -qi "\.ipynb";         then echo "Add/update Jupyter notebooks"
    elif echo "$files" | grep -qi "test\|spec";       then echo "Add/update test suite"
    elif echo "$files" | grep -qi "readme\|docs\|md"; then echo "Update documentation"
    elif echo "$files" | grep -qi "fix\|bug\|patch";  then echo "Fix identified bugs and issues"
    elif echo "$files" | grep -qi "\.yml\|\.yaml\|\.json\|\.toml"; then echo "Update configuration files"
    elif echo "$files" | grep -qi "\.sh\|\.bash";     then echo "Update shell scripts"
    elif echo "$files" | grep -qi "\.py";             then echo "Update Python source files"
    elif echo "$files" | grep -qi "\.js\|\.ts\|\.jsx\|\.tsx"; then echo "Update frontend source"
    else echo "Update project files"; fi
}

# ──────────────────────────────────────────────────────────────────────────────
#  MAIN FLOW
# ──────────────────────────────────────────────────────────────────────────────
trap 'spinner_stop; echo; error "Interrupted"; exit 130' INT TERM

print_banner
check_git
check_changes

# ── STAGE ────────────────────────────────────────────────────────────────────
section "📦" "STAGING"
spinner_start "Running git add ."
git add .
spinner_stop
log "All changes staged"

# ── COMMIT ───────────────────────────────────────────────────────────────────
section "✏️ " "COMMIT"
SUGGESTED="$(suggest_commit)"
echo
echo -e "  ${FG_CYAN}Suggested${RESET}  ${FG_GRAY}›${RESET}  ${ITALIC}${FG_AMBER}${SUGGESTED}${RESET}"
echo
printf "  ${FG_WHITE}${BOLD}Message${RESET} ${FG_GRAY}[press Enter to accept suggestion]${RESET}\n"
printf "  ${FG_AMBER}▸${RESET}  "
read -r MSG
MSG="${MSG:-$SUGGESTED}"
MSG="$(echo "$MSG" | sed 's/^ *//;s/ *$//')"   # trim

if [[ ${#MSG} -lt 5 ]]; then
    error "Commit message too short (min 5 chars)"
    exit 1
fi

spinner_start "Creating commit..."
sleep 0.3
spinner_stop
if ! git commit -m "$MSG" --quiet; then
    warn "Nothing new to commit (tree already clean)"
    exit 0
fi
log "Committed  ${FG_GRAY}\"${MSG}\"${RESET}"
dim_msg "SHA › $(git rev-parse --short HEAD)"

# ── PUSH WITH RETRY ──────────────────────────────────────────────────────────
section "🚀" "PUSH"
echo

attempt=1
while [[ $attempt -le $MAX_RETRIES ]]; do
    progress_bar "$attempt" "$MAX_RETRIES" "Attempt ${attempt} of ${MAX_RETRIES} → ${REMOTE}/${BRANCH}"
    echo

    spinner_start "Pushing to ${REMOTE}/${BRANCH}..."
    if git push "$REMOTE" "$BRANCH" --quiet 2>/dev/null; then
        spinner_stop
        echo
        echo -e "  ${BG_GREEN}${FG_WHITE}${BOLD}  ✔  PUSH SUCCESSFUL  ${RESET}"
        echo
        dim_msg "Remote  › ${REMOTE}"
        dim_msg "Branch  › ${BRANCH}"
        dim_msg "Commit  › $(git rev-parse --short HEAD)  \"${MSG}\""
        hr
        echo
        exit 0
    else
        spinner_stop
        warn "Push failed — attempt ${attempt}/${MAX_RETRIES}"
        [[ $attempt -lt $MAX_RETRIES ]] && { dim_msg "Retrying in 2 s…"; sleep 2; }
    fi
    attempt=$((attempt + 1))
done

# ── FAILURE ──────────────────────────────────────────────────────────────────
echo
echo -e "  ${BG_RED}${FG_WHITE}${BOLD}  ✖  ALL PUSH ATTEMPTS FAILED  ${RESET}"
echo
error "Push failed after ${MAX_RETRIES} retries"
echo
section "💡" "RECOVERY STEPS"
echo
echo -e "  ${FG_AMBER}${BOLD}1.${RESET}  ${FG_WHITE}git pull --rebase ${REMOTE} ${BRANCH}${RESET}"
echo -e "  ${FG_AMBER}${BOLD}2.${RESET}  ${FG_WHITE}git push ${REMOTE} ${BRANCH}${RESET}"
hr
echo
exit 1