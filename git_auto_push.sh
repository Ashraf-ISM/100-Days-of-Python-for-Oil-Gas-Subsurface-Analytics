#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                                                                            ║
# ║    ███████  ██████  ██████   ██████  ███████                               ║
# ║    ██      ██    ██ ██   ██ ██       ██                                    ║
# ║    █████   ██    ██ ██████  ██   ███ █████                                 ║
# ║    ██      ██    ██ ██   ██ ██    ██ ██                                    ║
# ║    ██       ██████  ██   ██  ██████  ███████                               ║
# ║                                                                            ║
# ║    GIT AUTO-PUSH  ·  FORGE EDITION  ·  v6.0                               ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
#
#  FEATURES
#    ›  Smart commit message suggestion via diff heuristics
#    ›  Multi-remote targeting with interactive selector
#    ›  Branch divergence detection & upstream sync check
#    ›  Per-filetype diff breakdown with add/remove counters
#    ›  Network latency probe before push
#    ›  Live pipeline stage tracker
#    ›  Rollback instructions on failure
#    ›  Deploy receipt with commit fingerprint
#    ›  Session log saved to ~/.gitautopush/logs/

set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
#  TERMINAL
# ─────────────────────────────────────────────────────────────────────────────
TERM_W=$(tput cols 2>/dev/null || echo 80)
_nc=$(tput colors 2>/dev/null || echo 0)
if [[ "$_nc" -lt 8 ]]; then
    echo "[forge] 256-color terminal required."; exit 1
fi

# ─────────────────────────────────────────────────────────────────────────────
#  COLORS  —  FORGE  (electric cyan × blue × white)
# ─────────────────────────────────────────────────────────────────────────────
R=$'\033[0m'
BOLD=$'\033[1m'
DIM=$'\033[2m'
IT=$'\033[3m'

C_CYAN=$'\033[38;5;51m'
C_CYAN2=$'\033[38;5;45m'
C_BLUE=$'\033[38;5;39m'
C_ICE=$'\033[38;5;123m'
C_SKY=$'\033[38;5;117m'

C_WHITE=$'\033[38;5;255m'
C_SILVER=$'\033[38;5;252m'
C_MIST=$'\033[38;5;247m'
C_SMOKE=$'\033[38;5;242m'
C_COAL=$'\033[38;5;238m'

C_GREEN=$'\033[38;5;120m'
C_GREEN2=$'\033[38;5;114m'
C_RED=$'\033[38;5;203m'
C_YELLOW=$'\033[38;5;228m'
C_ORANGE=$'\033[38;5;215m'

# ─────────────────────────────────────────────────────────────────────────────
#  SESSION INIT
# ─────────────────────────────────────────────────────────────────────────────
LOG_DIR="${HOME}/.gitautopush/logs"
mkdir -p "$LOG_DIR"
SESSION_LOG="${LOG_DIR}/$(date '+%Y%m%d_%H%M%S')_deploy.log"

if command -v sha256sum &>/dev/null; then
    SESSION_ID=$(printf '%s' "$(date +%s%N 2>/dev/null || date +%s)$$" \
        | sha256sum | head -c 16 | tr '[:lower:]' '[:upper:]')
else
    SESSION_ID=$(printf '%s' "$(date +%s)$$" \
        | md5sum 2>/dev/null | head -c 16 | tr '[:lower:]' '[:upper:]' \
        || date +%s | head -c 16)
fi

_log() { printf '[%s] %s\n' "$(date '+%H:%M:%S')" "$*" >> "$SESSION_LOG" 2>/dev/null || true; }
_log "SESSION OPEN · ID=${SESSION_ID}"

# ─────────────────────────────────────────────────────────────────────────────
#  CURSOR CONTROL
# ─────────────────────────────────────────────────────────────────────────────
_hide_cursor() { tput civis 2>/dev/null || true; }
_show_cursor() { tput cnorm 2>/dev/null || true; }
_cleanup()     { _show_cursor; printf '\n'; _log "SESSION CLOSE"; }
trap _cleanup EXIT INT TERM

# ─────────────────────────────────────────────────────────────────────────────
#  UTILITIES
# ─────────────────────────────────────────────────────────────────────────────
_rpt() {
    local char="$1" n="$2" o="" i=0
    while [[ $i -lt $n ]]; do o+="$char"; i=$(( i+1 )); done
    printf '%s' "$o"
}

_strip() { printf '%s' "$1" | sed 's/\x1b\[[0-9;]*[mK]//g'; }
_vlen()  { local s; s=$(_strip "$1"); printf '%d' "${#s}"; }

# ─────────────────────────────────────────────────────────────────────────────
#  SPINNER
# ─────────────────────────────────────────────────────────────────────────────
_spinner() {
    local pid="$1" msg="${2:-Working}" done_msg="${3:-Done}"
    local frames=('⣾' '⣽' '⣻' '⢿' '⡿' '⣟' '⣯' '⣷')
    local i=0 elapsed=0
    _hide_cursor
    while kill -0 "$pid" 2>/dev/null; do
        local f="${frames[$(( i % 8 ))]}"
        local s=$(( elapsed / 10 ))
        printf '\r    %b%s%b  %b%s%b  %b%ds%b   ' \
            "${C_CYAN}${BOLD}" "$f" "$R" \
            "${C_SILVER}" "$msg" "$R" \
            "${DIM}" "$s" "$R"
        i=$(( i+1 )); elapsed=$(( elapsed+1 ))
        sleep 0.1
    done
    _show_cursor
    printf '\r    %b✔%b  %b%s%b%-40s\n' \
        "${C_GREEN}${BOLD}" "$R" "${C_WHITE}" "$done_msg" "$R" " "
}

# ─────────────────────────────────────────────────────────────────────────────
#  PROGRESS BAR
# ─────────────────────────────────────────────────────────────────────────────
_progress() {
    local dur="${1:-0.6}" label="${2:-}" style="${3:-1}"
    local w=44
    local delay
    delay=$(echo "scale=5; $dur / $w" | bc 2>/dev/null || echo "0.014")

    # color ramps (256-color indices)
    local s1=(51 45 39 33 27 21 57 93)
    local s2=(120 114 108 114 120 156 192 228)
    local s3=(228 222 215 208 203 197 196 160)

    _hide_cursor
    local i=0
    while [[ $i -le $w ]]; do
        local pct=$(( i * 100 / w ))
        local bar="" f=0
        while [[ $f -lt $i ]]; do
            local gi=$(( f * 7 / (w > 0 ? w : 1) ))
            case $style in
                1) bar+=$'\033[38;5;'"${s1[$gi]}m█" ;;
                2) bar+=$'\033[38;5;'"${s2[$gi]}m█" ;;
                *) bar+=$'\033[38;5;'"${s3[$gi]}m█" ;;
            esac
            f=$(( f+1 ))
        done
        local empty
        empty=$(_rpt '░' $(( w - i )))
        printf '\r    %b%b%b%b%s%b  %b%3d%%%b  %b%s%b' \
            "" "$bar" "$R" "${DIM}" "$empty" "$R" \
            "${C_CYAN}${BOLD}" "$pct" "$R" \
            "${DIM}${IT}" "$label" "$R"
        sleep "$delay"
        i=$(( i+1 ))
    done
    _show_cursor
    printf '\n'
    _log "Progress: $label"
}

# ─────────────────────────────────────────────────────────────────────────────
#  SECTION HEADER
# ─────────────────────────────────────────────────────────────────────────────
_section() {
    local num="$1" title="$2"
    local W=72
    printf '\n  %b' "${C_COAL}"
    _rpt '─' $W
    printf '%b\n' "$R"
    printf '  %b%b ▌%02d▐ %b%b  %b%b%-50s%b\n' \
        "${C_CYAN}${BOLD}" "" "$num" "" "$R" \
        "${BOLD}" "${C_WHITE}" "$title" "$R"
    printf '  %b' "${C_COAL}"
    _rpt '─' $W
    printf '%b\n\n' "$R"
    _log "=== STAGE ${num}: ${title} ==="
}

# ─────────────────────────────────────────────────────────────────────────────
#  STATUS LINES
# ─────────────────────────────────────────────────────────────────────────────
_ok()   { printf '    %b✔%b  %b%s%b\n' "${C_GREEN}${BOLD}" "$R" "${C_SILVER}" "$1" "$R";  _log "OK  $(_strip "$1")"; }
_warn() { printf '    %b!%b  %b%s%b\n' "${C_YELLOW}${BOLD}" "$R" "${C_YELLOW}" "$1" "$R"; _log "WRN $(_strip "$1")"; }
_err()  { printf '    %b✖%b  %b%s%b\n' "${C_RED}${BOLD}" "$R" "${C_RED}" "$1" "$R";       _log "ERR $(_strip "$1")"; }
_info() { printf '    %b◆%b  %b%s%b\n' "${C_SKY}${BOLD}" "$R" "${DIM}" "$1" "$R";         _log "INF $(_strip "$1")"; }
_run()  { printf '    %b›%b  %b%s%b\n' "${C_CYAN}${BOLD}" "$R" "${C_SILVER}" "$1" "$R";   _log "RUN $(_strip "$1")"; }
_sub()  { printf '      %b%s%b\n' "${DIM}" "$1" "$R"; }
_kv()   { printf '    %b%-18s%b  %b%s%b\n' "${DIM}" "$1" "$R" "${C_WHITE}" "$2" "$R"; }

# ─────────────────────────────────────────────────────────────────────────────
#  DATA CARD
# ─────────────────────────────────────────────────────────────────────────────
CW=64

_card_open() {
    local title="${1:-}" accent="${2:-${C_COAL}}"
    local tlen=${#title}
    local d=$(( CW - tlen - 2 ))
    [[ $d -lt 1 ]] && d=1
    printf '  %b╔═ %b%b%s%b %b%b╗%b\n' \
        "$accent" \
        "${BOLD}${C_CYAN}" "$title" "$R" \
        "$accent" "$(_rpt '═' $d)" "" "$R"
}

_card_row() {
    local k="$1" v="$2"
    local kl vl pad
    kl=$(_vlen "$k"); vl=$(_vlen "$v")
    pad=$(( CW - kl - vl ))
    [[ $pad -lt 1 ]] && pad=1
    printf '  %b║%b  %b%s%b  %b%s%b%*s%b║%b\n' \
        "${C_COAL}" "$R" \
        "${DIM}" "$k" "$R" \
        "" "$v" "$R" \
        "$pad" "" \
        "${C_COAL}" "$R"
}

_card_sep() {
    printf '  %b╠%s╣%b\n' "${C_COAL}" "$(_rpt '═' $(( CW+2 )))" "$R"
}

_card_close() {
    printf '  %b╚%s╝%b\n' "${C_COAL}" "$(_rpt '═' $(( CW+2 )))" "$R"
}

# ─────────────────────────────────────────────────────────────────────────────
#  FILE TYPE BADGE
# ─────────────────────────────────────────────────────────────────────────────
_badge() {
    local f="$1"
    case "$f" in
        *.js|*.mjs)          printf '%bJS  %b' "${C_YELLOW}" "$R" ;;
        *.ts|*.tsx|*.jsx)    printf '%bTS  %b' "${C_BLUE}" "$R" ;;
        *.py)                printf '%bPY  %b' "${C_SKY}" "$R" ;;
        *.go)                printf '%bGO  %b' "${C_CYAN2}" "$R" ;;
        *.rs)                printf '%bRS  %b' "${C_ORANGE}" "$R" ;;
        *.sh|*.bash|*.zsh)   printf '%bSH  %b' "${C_GREEN}" "$R" ;;
        *.json)              printf '%bJSON%b' "${C_MIST}" "$R" ;;
        *.yaml|*.yml)        printf '%bYAML%b' "${C_MIST}" "$R" ;;
        *.md|*.rst|*.txt)    printf '%bDOC %b' "${C_SMOKE}" "$R" ;;
        *.css|*.scss|*.sass) printf '%bCSS %b' "${C_ICE}" "$R" ;;
        *.html|*.htm)        printf '%bHTML%b' "${C_ORANGE}" "$R" ;;
        *.sql)               printf '%bSQL %b' "${C_YELLOW}" "$R" ;;
        Dockerfile*|*.dock*) printf '%bDKR %b' "${C_BLUE}" "$R" ;;
        *.lock|*.sum)        printf '%bLOCK%b' "${C_SMOKE}" "$R" ;;
        *.pdf)               printf '%bPDF %b' "${C_RED}" "$R" ;;
        *.png|*.jpg|*.gif|*.svg|*.webp) printf '%bIMG %b' "${C_ICE}" "$R" ;;
        *.ipynb)             printf '%bIPYN%b' "${C_ORANGE}" "$R" ;;
        *)                   printf '%b··· %b' "${C_COAL}" "$R" ;;
    esac
}

# ─────────────────────────────────────────────────────────────────────────────
#  DIFF STATS
# ─────────────────────────────────────────────────────────────────────────────
_diff_stats() {
    local diff_stat
    diff_stat=$(git diff --cached --stat 2>/dev/null | head -25)
    [[ -z "$diff_stat" ]] && return
    printf '\n    %bStaged deltas:%b\n\n' "${DIM}" "$R"
    while IFS= read -r line; do
        [[ "$line" != *"|"* ]] && continue
        local fname changes adds dels
        fname=$(printf '%s' "$line" | awk -F'|' '{print $1}' | sed 's/^ *//;s/ *$//')
        changes=$(printf '%s' "$line" | awk -F'|' '{print $2}')
        adds=$(printf '%s' "$changes" | grep -o '+' | wc -l | tr -d ' ')
        dels=$(printf '%s' "$changes" | grep -o '-' | wc -l | tr -d ' ')
        printf '    %b[%b%b%b]%b  %b%-36s%b  %b+%d%b  %b-%d%b\n' \
            "${C_COAL}" "$R" "$(_badge "$fname")" "${C_COAL}" "$R" \
            "${DIM}" "$fname" "$R" \
            "${C_GREEN}" "$adds" "$R" \
            "${C_RED}" "$dels" "$R"
    done <<< "$diff_stat"
}

# ─────────────────────────────────────────────────────────────────────────────
#  COMMIT MESSAGE SUGGESTION
# ─────────────────────────────────────────────────────────────────────────────
_suggest() {
    local files
    files=$(git diff --cached --name-only 2>/dev/null)
    local msg=""

    if   printf '%s' "$files" | grep -qi "test\|spec";                      then msg="Add test coverage for updated modules"
    elif printf '%s' "$files" | grep -qi "readme\|docs\|\.md\|\.rst";       then msg="Update project documentation"
    elif printf '%s' "$files" | grep -qi "\.lock\|package\.json\|go\.sum\|cargo\.toml\|requirements"; then msg="Upgrade dependency versions"
    elif printf '%s' "$files" | grep -qi "dockerfile\|docker-compose\|\.yml\|\.yaml"; then msg="Revise deployment configuration"
    elif printf '%s' "$files" | grep -qi "config\|settings\|\.env";         then msg="Adjust environment configuration"
    elif printf '%s' "$files" | grep -qi "auth\|login\|token\|session";     then msg="Strengthen authentication layer"
    elif printf '%s' "$files" | grep -qi "api\|endpoint\|route\|handler";   then msg="Extend API surface"
    elif printf '%s' "$files" | grep -qi "refactor\|clean\|lint\|format";   then msg="Refactor for clarity and consistency"
    elif printf '%s' "$files" | grep -qi "fix\|bug\|patch\|hotfix";         then msg="Resolve defect in affected components"
    elif printf '%s' "$files" | grep -qi "\.ipynb\|notebook";               then msg="Add analysis notebook"
    elif printf '%s' "$files" | grep -qi "\.py";                            then msg="Update Python module"
    fi

    if [[ -z "$msg" ]]; then
        local n
        n=$(printf '%s\n' "$files" | grep -c . 2>/dev/null || echo 0)
        if [[ $n -gt 5 ]]; then
            msg="Refactor across multiple modules"
        else
            local fn
            fn=$(printf '%s\n' "$files" | head -1 | xargs basename 2>/dev/null || echo "files")
            msg="Update ${fn}"
        fi
    fi
    printf '%s' "$msg"
}

# ─────────────────────────────────────────────────────────────────────────────
#  NETWORK CHECK
# ─────────────────────────────────────────────────────────────────────────────
_net_check() {
    local url="$1"
    local host
    host=$(printf '%s' "$url" | sed 's|.*@||;s|:.*||;s|/.*||;s|\.git$||' 2>/dev/null || echo "github.com")
    printf '    %bProbing %s…%b\n' "${DIM}" "$host" "$R"
    local lat="—"
    if command -v ping &>/dev/null; then
        lat=$(ping -c 1 -W 2 "$host" 2>/dev/null \
            | grep 'time=' | sed 's/.*time=//;s/ ms.*//' | head -1 || echo "—")
    fi
    if [[ "$lat" == "—" || -z "$lat" ]]; then
        _warn "Cannot reach ${host} — proceeding anyway"
    else
        _ok "${C_CYAN}${host}${R}${C_SILVER} reachable  ${DIM}rtt ${C_CYAN}${lat}ms${R}"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
#  DIVERGENCE CHECK
# ─────────────────────────────────────────────────────────────────────────────
_diverge() {
    local a b
    a=$(git rev-list --count "@{upstream}..HEAD" 2>/dev/null || echo "0")
    b=$(git rev-list --count "HEAD..@{upstream}" 2>/dev/null || echo "0")
    if [[ "$b" -gt 0 ]]; then
        _warn "Local is ${C_RED}${b}${C_YELLOW} commits behind remote — consider rebasing"
    elif [[ "$a" -gt 0 ]]; then
        _info "Local is ${C_GREEN}${a}${DIM} commits ahead of remote"
    else
        _ok "Branch synchronized with upstream"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
#  HASH FINGERPRINT DISPLAY
# ─────────────────────────────────────────────────────────────────────────────
_hash_display() {
    local hash="$1"
    local pal=(51 45 39 33 27 21 57 93 129 165)
    printf '\n    %bCOMMIT FINGERPRINT%b  ' "${DIM}" "$R"
    local i=0
    while [[ $i -lt ${#hash} && $i -lt 40 ]]; do
        local pair="${hash:$i:2}"
        local ci=$(( (i / 2) % 10 ))
        printf $'\033[38;5;%dm%s\033[0m' "${pal[$ci]}" "$pair"
        [[ $(( (i+2) % 8 )) -eq 0 && $i -lt 38 ]] && printf '%b·%b' "${DIM}" "$R"
        i=$(( i+2 ))
    done
    printf '\n'
}

# ─────────────────────────────────────────────────────────────────────────────
#  PIPELINE TRACKER
# ─────────────────────────────────────────────────────────────────────────────
PIPE_STAGES=("INIT" "SCAN" "MSG" "TARGET" "CONFIRM" "EXECUTE" "SEALED")

_pipeline() {
    local cur="$1" total=${#PIPE_STAGES[@]}
    printf '\n  '
    local i=0
    while [[ $i -lt $total ]]; do
        local s="${PIPE_STAGES[$i]}"
        if   [[ $i -lt $cur ]]; then printf '%b✔ %-8s%b' "${C_GREEN}${BOLD}" "$s" "$R"
        elif [[ $i -eq $cur ]]; then printf '%b● %-8s%b' "${C_CYAN}${BOLD}"  "$s" "$R"
        else                         printf '%b○ %-8s%b' "${DIM}"             "$s" "$R"
        fi
        [[ $i -lt $(( total-1 )) ]] && printf '%b╌%b' "${C_COAL}" "$R"
        i=$(( i+1 ))
    done
    printf '\n\n'
}

# ─────────────────────────────────────────────────────────────────────────────
#  BANNER
# ─────────────────────────────────────────────────────────────────────────────
_banner() {
    clear; _hide_cursor; sleep 0.05

    local W=76
    printf '\n  %b' "${C_CYAN}${BOLD}"; _rpt '═' $W; printf '%b\n' "$R"

    # Brand line
    printf '  %b║%b  ' "${C_CYAN}${BOLD}" "$R"
    printf '%b%bFORGE%b' "${BOLD}" "${C_WHITE}" "$R"
    printf '  %b·%b  %b%bGIT AUTO-PUSH%b  %b·%b  %bTERMINAL EDITION%b  %b·%b  %bv6.0%b' \
        "${DIM}" "$R" "${C_CYAN}${BOLD}" "" "$R" \
        "${DIM}" "$R" "${DIM}" "$R" \
        "${DIM}" "$R" "${C_SMOKE}" "$R"
    # right-pad + close
    printf '%26s%b║%b\n' "" "${C_CYAN}${BOLD}" "$R"

    # Mid separator
    printf '  %b╠%b' "${C_CYAN}${BOLD}" "$R"
    printf '%b'; _rpt '─' $(( W-2 )); printf '%b' "$R"
    printf '%b╣%b\n' "${C_CYAN}${BOLD}" "$R"

    # Session line
    printf '  %b║%b  %bSESSION%b  %b│%b  %b%b%s%b  %b│%b  %b%s%b' \
        "${C_CYAN}${BOLD}" "$R" \
        "${DIM}" "$R" "${C_COAL}" "$R" \
        "${C_CYAN}${BOLD}" "" "$SESSION_ID" "$R" \
        "${C_COAL}" "$R" \
        "${DIM}" "$(date '+%Y-%m-%d  %H:%M:%S  %Z')" "$R"
    local spad=$(( W - 12 - ${#SESSION_ID} - 26 - 1 ))
    [[ $spad -lt 1 ]] && spad=1
    printf '%*s%b║%b\n' "$spad" "" "${C_CYAN}${BOLD}" "$R"

    # Log line
    printf '  %b║%b  %bLOG%b     %b│%b  %b%s%b' \
        "${C_CYAN}${BOLD}" "$R" "${DIM}" "$R" "${C_COAL}" "$R" "${C_SMOKE}" "$SESSION_LOG" "$R"
    local lpad=$(( W - 14 - ${#SESSION_LOG} - 1 ))
    [[ $lpad -lt 1 ]] && lpad=1
    printf '%*s%b║%b\n' "$lpad" "" "${C_CYAN}${BOLD}" "$R"

    printf '  %b' "${C_CYAN}${BOLD}"; _rpt '═' $W; printf '%b\n\n' "$R"
    _show_cursor; sleep 0.1
}

# ═════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═════════════════════════════════════════════════════════════════════════════
_banner

# ── 01 INITIALIZATION ─────────────────────────────────────────────────────────
_section "01" "ENVIRONMENT INITIALIZATION"
_pipeline 0

if ! command -v git &>/dev/null; then
    _err "Git not found in \$PATH"
    _sub "Install: https://git-scm.com/downloads"
    printf '\n'; exit 1
fi
_ok "Git  ${DIM}·${R}  ${C_CYAN}$(git --version | sed 's/git version //')${R}"
sleep 0.03

if ! git rev-parse --git-dir &>/dev/null 2>&1; then
    _err "Not inside a Git repository"
    _sub "Run \`git init\` or cd into an existing repo"
    printf '\n'; exit 1
fi
_ok "Repository validated"
sleep 0.03

BRANCH=$(git branch --show-current 2>/dev/null || echo "HEAD")
REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "—")
LAST_COMMIT=$(git log -1 --pretty=format:"%h  %s  ·  %cr" 2>/dev/null || echo "No commits")
TOTAL_COMMITS=$(git rev-list --count HEAD 2>/dev/null || echo "0")
GIT_AUTHOR=$(git config user.name 2>/dev/null || echo "Unknown")
GIT_EMAIL=$(git config user.email 2>/dev/null || echo "")
REPO_NAME=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)" || echo "unknown")
STASH_COUNT=$(git stash list 2>/dev/null | grep -c . 2>/dev/null || echo "0")

printf '\n'
_card_open "Repository State" "${C_COAL}"
_card_row "${DIM}repository${R}"    "${C_CYAN}${BOLD}${REPO_NAME}${R}"
_card_row "${DIM}branch${R}"        "${C_WHITE}${BOLD}${BRANCH}${R}"
_card_row "${DIM}remote${R}"        "${DIM}${REMOTE_URL}${R}"
_card_row "${DIM}author${R}"        "${C_SILVER}${GIT_AUTHOR}  <${GIT_EMAIL}>${R}"
_card_row "${DIM}last commit${R}"   "${DIM}${LAST_COMMIT}${R}"
_card_row "${DIM}commits${R}"       "${C_GREEN}${BOLD}${TOTAL_COMMITS}${R}"
[[ "$STASH_COUNT" -gt 0 ]] && \
    _card_row "${DIM}stash${R}" "${C_YELLOW}${BOLD}${STASH_COUNT}${R}  ${DIM}pending entries${R}"
_card_close
printf '\n'

_diverge 2>/dev/null || true

# ── 02 WORKING TREE SCAN ──────────────────────────────────────────────────────
_section "02" "WORKING TREE ANALYSIS"
_pipeline 1

STATUS_OUTPUT=$(git status --short 2>/dev/null || echo "")

if [[ -z "$STATUS_OUTPUT" ]]; then
    _warn "Working tree is clean — nothing to commit"
    _sub "Make changes and retry."
    printf '\n'; exit 0
fi

N_MOD=0; N_ADD=0; N_DEL=0; N_UNT=0; N_REN=0; N_OTH=0

while IFS= read -r line; do
    flag="${line:0:2}"
    file="${line:3}"
    bdg=$(_badge "$file")
    case "$flag" in
        "M "|" M"|"MM"|"AM")
            N_MOD=$(( N_MOD+1 ))
            printf '    %b≋%b  [%s]  %b%-10s%b  %b%s%b\n' \
                "${C_YELLOW}${BOLD}" "$R" "$bdg" "${DIM}" "modified"  "$R" "${C_SILVER}" "$file" "$R" ;;
        "A "|" A")
            N_ADD=$(( N_ADD+1 ))
            printf '    %b+%b  [%s]  %b%-10s%b  %b%s%b\n' \
                "${C_GREEN}${BOLD}" "$R" "$bdg"  "${DIM}" "new file"  "$R" "${C_WHITE}"  "$file" "$R" ;;
        "D "|" D")
            N_DEL=$(( N_DEL+1 ))
            printf '    %b−%b  [%s]  %b%-10s%b  %b%s%b\n' \
                "${C_RED}${BOLD}" "$R"    "$bdg" "${DIM}" "deleted"   "$R" "${DIM}"      "$file" "$R" ;;
        "??")
            N_UNT=$(( N_UNT+1 ))
            printf '    %b?%b  [%s]  %b%-10s%b  %b%s%b\n' \
                "${C_SMOKE}${BOLD}" "$R" "$bdg" "${DIM}" "untracked" "$R" "${DIM}"      "$file" "$R" ;;
        "R "|" R"|"RM"|"RD")
            N_REN=$(( N_REN+1 ))
            printf '    %b→%b  [%s]  %b%-10s%b  %b%s%b\n' \
                "${C_ICE}${BOLD}" "$R"  "$bdg" "${DIM}" "renamed"   "$R" "${C_SILVER}" "$file" "$R" ;;
        *)
            N_OTH=$(( N_OTH+1 ))
            printf '    %b·%b  [%s]  %b%s%b\n' \
                "${C_SMOKE}" "$R" "$bdg" "${DIM}" "$file" "$R" ;;
    esac
done <<< "$STATUS_OUTPUT"

TOTAL=$(printf '%s\n' "$STATUS_OUTPUT" | grep -c . 2>/dev/null || echo 0)

printf '\n'
_card_open "Change Breakdown" "${C_COAL}"
[[ $N_MOD -gt 0 ]] && _card_row "${DIM}modified${R}"  "${C_YELLOW}${BOLD}${N_MOD}${R}  ${DIM}file(s)${R}"
[[ $N_ADD -gt 0 ]] && _card_row "${DIM}added${R}"     "${C_GREEN}${BOLD}${N_ADD}${R}  ${DIM}file(s)${R}"
[[ $N_DEL -gt 0 ]] && _card_row "${DIM}deleted${R}"   "${C_RED}${BOLD}${N_DEL}${R}  ${DIM}file(s)${R}"
[[ $N_UNT -gt 0 ]] && _card_row "${DIM}untracked${R}" "${C_SMOKE}${BOLD}${N_UNT}${R}  ${DIM}file(s)${R}"
[[ $N_REN -gt 0 ]] && _card_row "${DIM}renamed${R}"   "${C_ICE}${BOLD}${N_REN}${R}  ${DIM}file(s)${R}"
_card_sep
_card_row "${BOLD}${C_WHITE}TOTAL${R}" "${C_CYAN}${BOLD}${TOTAL}${R}  ${DIM}file(s) detected${R}"
_card_close

# ── 03 COMMIT MESSAGE ─────────────────────────────────────────────────────────
_section "03" "COMMIT MESSAGE"
_pipeline 2

SUGGESTED=$(_suggest)
printf '    %bSuggestion%b  %b›%b  %b%s%b  %b(↵ to accept)%b\n' \
    "${DIM}" "$R" "${C_COAL}" "$R" "${IT}${C_SKY}" "$SUGGESTED" "$R" "${DIM}" "$R"
printf '    %bConvention%b  %b›%b  %bImperative · ≤72 chars · no trailing period%b\n' \
    "${DIM}" "$R" "${C_COAL}" "$R" "${DIM}" "$R"
printf '\n    %b›%b  %b' "${C_CYAN}${BOLD}" "$R" "${C_WHITE}"
read -r commit_message
printf '%b' "$R"

[[ -z "$commit_message" ]] && commit_message="$SUGGESTED"
if [[ -z "$commit_message" ]]; then
    _err "Commit message required"; printf '\n'; exit 1
fi

# Quality
MSG_LEN=${#commit_message}
if   [[ $MSG_LEN -lt 5  ]]; then QUALITY="${C_RED}${BOLD}Too short${R}";     Q_SCORE=1
elif [[ $MSG_LEN -lt 15 ]]; then QUALITY="${C_RED}${BOLD}Minimal${R}";       Q_SCORE=2
elif [[ $MSG_LEN -lt 30 ]]; then QUALITY="${C_YELLOW}${BOLD}Acceptable${R}"; Q_SCORE=3
elif [[ $MSG_LEN -lt 50 ]]; then QUALITY="${C_GREEN2}${BOLD}Good${R}";       Q_SCORE=4
elif [[ $MSG_LEN -lt 72 ]]; then QUALITY="${C_GREEN}${BOLD}Ideal ✓${R}";     Q_SCORE=5
else                              QUALITY="${C_SMOKE}${BOLD}Too long${R}";    Q_SCORE=2; fi

FIRST_WORD=$(printf '%s' "$commit_message" | awk '{print $1}')
if printf '%s' "$FIRST_WORD" | grep -qiE "^(added|fixed|updated|removed|changed|created|deleted|modified)ed?$"; then
    TONE="${C_YELLOW}Past tense — prefer imperative${R}"
else
    TONE="${C_GREEN}Imperative tone ✓${R}"
fi

QBAR=""
qi=1
while [[ $qi -le 5 ]]; do
    [[ $qi -le $Q_SCORE ]] && QBAR+="${C_CYAN}▮" || QBAR+="${C_COAL}▯"
    qi=$(( qi+1 ))
done
QBAR+="$R"

printf '\n'
_card_open "Message Analysis" "${C_COAL}"
_card_row "${DIM}message${R}" "${BOLD}${C_WHITE}\"${commit_message}\"${R}"
_card_row "${DIM}length${R}"  "${C_SILVER}${BOLD}${MSG_LEN}${R}  ${DIM}chars${R}"
_card_row "${DIM}quality${R}" "${QBAR}  ${QUALITY}"
_card_row "${DIM}tone${R}"    "${TONE}"
_card_close

# ── 04 REMOTE TARGETING ───────────────────────────────────────────────────────
_section "04" "TARGET CONFIGURATION"
_pipeline 3

REMOTES_LIST=$(git remote 2>/dev/null || echo "origin")
REMOTE_COUNT=$(printf '%s\n' "$REMOTES_LIST" | grep -c . 2>/dev/null || echo 1)
PUSH_REMOTE="origin"

if [[ $REMOTE_COUNT -gt 1 ]]; then
    printf '    %bAvailable remotes:%b\n\n' "${DIM}" "$R"
    ri=1
    while IFS= read -r r; do
        rurl=$(git remote get-url "$r" 2>/dev/null || echo "—")
        printf '    %b[%d]%b  %b%s%b  %b→%b  %b%s%b\n' \
            "${C_CYAN}${BOLD}" "$ri" "$R" "${C_WHITE}" "$r" "$R" \
            "${C_COAL}" "$R" "${DIM}" "$rurl" "$R"
        ri=$(( ri+1 ))
    done <<< "$REMOTES_LIST"
    printf '\n    %b›%b  %bRemote [default: origin]:%b  %b' \
        "${C_CYAN}${BOLD}" "$R" "${DIM}" "$R" "${C_WHITE}"
    read -r chosen_remote
    printf '%b' "$R"
    [[ -n "$chosen_remote" ]] && PUSH_REMOTE="$chosen_remote"
fi

PUSH_URL=$(git remote get-url "$PUSH_REMOTE" 2>/dev/null || echo "—")
printf '\n'
_kv "push target" "${C_CYAN}${BOLD}${PUSH_REMOTE}${R}${C_SMOKE}/${R}${C_WHITE}${BOLD}${BRANCH}${R}"
_kv "remote url"  "${DIM}${PUSH_URL}${R}"
printf '\n'
_net_check "$PUSH_URL"

# ── 05 CONFIRM ────────────────────────────────────────────────────────────────
_section "05" "CONFIRM DEPLOYMENT"
_pipeline 4

printf '\n'
_card_open "Deployment Brief" "${C_COAL}"
_card_row "${DIM}repository${R}"  "${C_CYAN}${BOLD}${REPO_NAME}${R}"
_card_row "${DIM}destination${R}" "${C_WHITE}${BOLD}${PUSH_REMOTE}${R}${C_SMOKE}/${R}${C_WHITE}${BOLD}${BRANCH}${R}"
_card_row "${DIM}message${R}"     "${IT}\"${commit_message}\"${R}"
_card_row "${DIM}scope${R}"       "${C_CYAN}${BOLD}${TOTAL}${R}  ${DIM}file(s) will be committed${R}"
_card_row "${DIM}author${R}"      "${C_SILVER}${GIT_AUTHOR}  <${GIT_EMAIL}>${R}"
_card_row "${DIM}session${R}"     "${DIM}${SESSION_ID}${R}"
_card_close
printf '\n'

CONFIRM_TIMEOUT=30
printf '    %b›%b  %bAuthorize deployment?%b  %b[y/N]%b  %bauto-abort %ds%b  %b' \
    "${C_CYAN}${BOLD}" "$R" "${C_WHITE}${BOLD}" "$R" \
    "${C_COAL}" "$R" "${DIM}" "$CONFIRM_TIMEOUT" "$R" "${C_WHITE}"

if read -r -t "$CONFIRM_TIMEOUT" confirm 2>/dev/null; then
    printf '%b\n' "$R"
else
    printf '%b\n' "$R"
    _warn "Timed out — deployment aborted"
    printf '\n'; exit 0
fi

if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    printf '\n'; _warn "Cancelled — no changes committed"; printf '\n'; exit 0
fi

# ── 06 PIPELINE EXECUTION ─────────────────────────────────────────────────────
_section "06" "PIPELINE EXECUTION"
_pipeline 5

# Start timer
if date +%s%N 2>/dev/null | grep -qE '^[0-9]{18,}'; then
    PIPE_START=$(date +%s%N); USE_NS=1
else
    PIPE_START=$(date +%s); USE_NS=0
fi

printf '\n'

# git add
_run "STAGE  ·  git add ."
git add . >/tmp/_ap_out 2>&1 &
_AP=$!
_spinner $_AP "Indexing working tree" "Staging complete"
wait $_AP
_progress 0.4 "Staging objects" 1
_diff_stats
printf '\n'

# git commit
_run "COMMIT  ·  Writing commit object"
git commit -m "$commit_message" >/tmp/_ap_out 2>&1 &
_CP=$!
_spinner $_CP "Persisting commit" "Commit recorded"
wait $_CP; CEXIT=$?

if [[ $CEXIT -ne 0 ]]; then
    printf '\n'; _err "Commit failed"
    while IFS= read -r ln; do _sub "$ln"; done < /tmp/_ap_out
    printf '\n'
    printf '    %bRollback:%b  %bgit reset HEAD~1%b\n' "${DIM}" "$R" "${C_ORANGE}" "$R"
    _log "COMMIT FAILED"; exit 1
fi
_progress 0.3 "Writing object tree" 2

NEW_HASH=$(git log -1 --pretty=format:"%H")
SHORT_HASH=$(git log -1 --pretty=format:"%h")
_hash_display "$NEW_HASH"
printf '\n'

# git push
_run "PUSH  ·  Transmitting to ${PUSH_REMOTE}/${BRANCH}"
git push -u "$PUSH_REMOTE" "$BRANCH" >/tmp/_ap_out 2>&1 &
_PP=$!
_spinner $_PP "Uploading pack objects" "Remote updated"
wait $_PP; PEXIT=$?

if [[ $PEXIT -ne 0 ]]; then
    printf '\n'; _err "Push rejected by remote"
    while IFS= read -r ln; do _sub "$ln"; done < /tmp/_ap_out
    printf '\n'
    printf '    %bRecovery:%b  %bgit pull --rebase %s %s%b\n' \
        "${DIM}" "$R" "${C_ORANGE}" "$PUSH_REMOTE" "$BRANCH" "$R"
    _log "PUSH FAILED"; exit 1
fi
_progress 0.65 "Transmitting deltas" 1
printf '\n'

# Elapsed
if [[ $USE_NS -eq 1 ]]; then
    PIPE_END=$(date +%s%N)
    ELAPSED_MS=$(( (PIPE_END - PIPE_START) / 1000000 ))
    ELAPSED_FMT="${ELAPSED_MS}ms"
else
    PIPE_END=$(date +%s)
    ELAPSED_FMT="$(( PIPE_END - PIPE_START ))s"
fi

# ─────────────────────────────────────────────────────────────────────────────
#  COMPLETION
# ─────────────────────────────────────────────────────────────────────────────
_pipeline 6

printf '\n'
SW=72
printf '  %b' "${C_CYAN}${BOLD}"; _rpt '═' $SW; printf '%b\n' "$R"

# success line
SUCCESS="   ✦  DEPLOY COMPLETE  ·  ALL STAGES NOMINAL   "
SL=${#SUCCESS}
SPAD=$(( SW - SL - 2 )); [[ $SPAD -lt 1 ]] && SPAD=1
printf '  %b║%b  %b%b%s%b%*s%b║%b\n' \
    "${C_CYAN}${BOLD}" "$R" "${BOLD}" "${C_WHITE}" "$SUCCESS" "$R" \
    "$SPAD" "" "${C_CYAN}${BOLD}" "$R"

SUBL="   Commit propagated · Remote updated · State sealed"
SBL=${#SUBL}; SBPAD=$(( SW - SBL - 2 )); [[ $SBPAD -lt 1 ]] && SBPAD=1
printf '  %b║%b  %b%s%b%*s%b║%b\n' \
    "${C_CYAN}${BOLD}" "$R" "${DIM}" "$SUBL" "$R" \
    "$SBPAD" "" "${C_CYAN}${BOLD}" "$R"

printf '  %b' "${C_CYAN}${BOLD}"; _rpt '═' $SW; printf '%b\n\n\n' "$R"

# Receipt
PUSHED_TIME=$(git log -1 --pretty=format:"%cr" 2>/dev/null || echo "just now")
REMOTE_REF="${PUSH_REMOTE}/${BRANCH}"

_card_open "◆  DEPLOYMENT RECEIPT" "${C_CYAN}"
printf '  %b║%b\n' "${C_COAL}" "$R"
_card_row "${DIM}repository${R}"  "${C_CYAN}${BOLD}${REPO_NAME}${R}"
_card_row "${DIM}destination${R}" "${C_WHITE}${BOLD}${BRANCH}${R}  ${C_COAL}→${R}  ${C_SKY}${REMOTE_REF}${R}"
_card_row "${DIM}commit${R}"      "${C_CYAN}${BOLD}${SHORT_HASH}${R}  ${DIM}${NEW_HASH}${R}"
_card_row "${DIM}message${R}"     "${IT}\"${commit_message}\"${R}"
_card_row "${DIM}files${R}"       "${C_WHITE}${BOLD}${TOTAL}${R}  ${DIM}changed${R}"
_card_row "${DIM}author${R}"      "${C_SILVER}${GIT_AUTHOR}  <${GIT_EMAIL}>${R}"
_card_row "${DIM}committed${R}"   "${C_GREEN}${PUSHED_TIME}${R}"
_card_row "${DIM}duration${R}"    "${C_CYAN}${ELAPSED_FMT}${R}"
_card_row "${DIM}session${R}"     "${DIM}${SESSION_ID}${R}"
_card_row "${DIM}log${R}"         "${C_SMOKE}${SESSION_LOG}${R}"
printf '  %b║%b\n' "${C_COAL}" "$R"
_card_close

printf '\n    %bForge Deploy  ·  Terminal Edition v6.0  ·  ~/.gitautopush/logs/%b\n\n' "${DIM}" "$R"

_log "DEPLOY SUCCESS | hash=${NEW_HASH} | branch=${BRANCH} | remote=${PUSH_REMOTE} | files=${TOTAL} | elapsed=${ELAPSED_FMT}"
rm -f /tmp/_ap_out
exit 0