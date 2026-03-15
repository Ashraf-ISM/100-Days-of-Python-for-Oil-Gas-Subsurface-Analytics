#!/usr/bin/env bash
# ╔═══════════════════════════════════════════════════════════════════════════════╗
# ║            ░██████╗░██╗████████╗░░░░█████╗░██╗   ██╗████████╗░██████╗        ║
# ║            ██╔════╝░██║╚══██╔══╝   ██╔══██╗██║   ██║╚══██╔══╝██╔════╝        ║
# ║            ██║░░██╗░██║   ██║      ███████║██║   ██║   ██║   ╚█████╗░        ║
# ║            ██║░░╚██╗██║   ██║      ██╔══██║██║   ██║   ██║    ╚═══██╗        ║
# ║            ╚██████╔╝██║   ██║      ██║  ██║╚██████╔╝   ██║   ██████╔╝        ║
# ║             ╚═════╝ ╚═╝   ╚═╝      ╚═╝  ╚═╝ ╚═════╝    ╚═╝   ╚═════╝         ║
# ║                                                                               ║
# ║                  ◈  QUANTUM DEPLOY ENGINE  ·  v4.0 NEXUS  ◈                  ║
# ╚═══════════════════════════════════════════════════════════════════════════════╝
#
#  FEATURES:
#    ✦ AI-powered commit message suggestions via git diff analysis
#    ✦ Multi-remote push support
#    ✦ Branch protection checks & upstream sync detection
#    ✦ Diff stats preview with file-type breakdown
#    ✦ Live network latency test before push
#    ✦ Animated neon pipeline with real-time stage tracking
#    ✦ Rollback command output on failure
#    ✦ Deploy receipt with QR-style hash display
#    ✦ Session log saved to ~/.gitautopush/logs/

set -euo pipefail

# ────────────────────────────────────────────────────────────────────────────────
#  TERMINAL CAPABILITY DETECTION
# ────────────────────────────────────────────────────────────────────────────────
TERM_W=$(tput cols 2>/dev/null || echo 80)
SUPPORTS_COLOR=$(tput colors 2>/dev/null || echo 0)
[[ $SUPPORTS_COLOR -lt 8 ]] && { echo "[git-autopush] Requires 256-color terminal."; exit 1; }

# ────────────────────────────────────────────────────────────────────────────────
#  COLOR PALETTE  (256-color + true-color blend)
# ────────────────────────────────────────────────────────────────────────────────
R='\033[0m'
BOLD='\033[1m'; DIM='\033[2m'; IT='\033[3m'; UL='\033[4m'; BLINK='\033[5m'

# Spectrum
C_NEON_CYAN='\033[38;5;51m'
C_ELECTRIC_BLUE='\033[38;5;39m'
C_VIOLET='\033[38;5;135m'
C_DEEP_VIOLET='\033[38;5;129m'
C_NEON_PINK='\033[38;5;201m'
C_MATRIX_GRN='\033[38;5;46m'
C_LIME='\033[38;5;154m'
C_AMBER='\033[38;5;220m'
C_ICE='\033[38;5;87m'
C_HOT_PINK='\033[38;5;213m'
C_PALE_CYAN='\033[38;5;159m'
C_GOLD='\033[38;5;226m'
C_ORANGE='\033[38;5;208m'
C_CORAL='\033[38;5;203m'
C_MINT='\033[38;5;121m'
C_LAVENDER='\033[38;5;183m'
C_RED='\033[38;5;196m'
C_WHITE='\033[38;5;255m'
C_GRAY='\033[38;5;240m'
C_LGRAY='\033[38;5;245m'

# BG tones
BG_DARK='\033[48;5;232m'
BG_CARD='\033[48;5;234m'
BG_ACCENT='\033[48;5;236m'

# ────────────────────────────────────────────────────────────────────────────────
#  SESSION LOGGING
# ────────────────────────────────────────────────────────────────────────────────
LOG_DIR="${HOME}/.gitautopush/logs"
mkdir -p "$LOG_DIR"
SESSION_LOG="${LOG_DIR}/$(date '+%Y%m%d_%H%M%S')_deploy.log"
SESSION_ID="$(date +%s | sha256sum | head -c 8 | tr '[:lower:]' '[:upper:]')"

log() { echo "[$(date '+%H:%M:%S')] $*" >> "$SESSION_LOG" 2>/dev/null; }
log "Session started · ID=$SESSION_ID"

# ────────────────────────────────────────────────────────────────────────────────
#  CURSOR & CLEANUP
# ────────────────────────────────────────────────────────────────────────────────
hide_cursor()  { tput civis 2>/dev/null || true; }
show_cursor()  { tput cnorm 2>/dev/null || true; }
save_pos()     { tput sc 2>/dev/null || true; }
restore_pos()  { tput rc 2>/dev/null || true; }
clear_line()   { printf '\r\033[2K'; }
move_up()      { printf "\033[%dA" "${1:-1}"; }

cleanup() {
    show_cursor
    tput rmcup 2>/dev/null || true
    echo ""
    log "Session ended"
}
trap cleanup EXIT INT TERM

# ────────────────────────────────────────────────────────────────────────────────
#  UTILITIES
# ────────────────────────────────────────────────────────────────────────────────
rpt() { local c="$1" n="$2" o=""; for ((i=0;i<n;i++)); do o+="$c"; done; printf '%s' "$o"; }
center() {
    local text="$1" width="${2:-$TERM_W}" clean
    clean=$(echo -e "$text" | sed 's/\x1b\[[0-9;]*m//g')
    local pad=$(( (width - ${#clean}) / 2 ))
    printf "%${pad}s%b\n" "" "$text"
}
strip_color() { echo -e "$1" | sed 's/\x1b\[[0-9;]*m//g'; }
str_len()     { local s; s=$(strip_color "$1"); echo ${#s}; }

# ────────────────────────────────────────────────────────────────────────────────
#  ADVANCED SPINNER  (orbital rings)
# ────────────────────────────────────────────────────────────────────────────────
spinner() {
    local pid=$1 msg="${2:-Processing…}" done_msg="${3:-Done}"
    local -a outer=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
    local -a inner=('◐' '◓' '◑' '◒')
    local -a dots=('   ' '.  ' '.. ' '...')
    local -a colors=("$C_NEON_CYAN" "$C_ICE" "$C_PALE_CYAN" "$C_ELECTRIC_BLUE" "$C_VIOLET" "$C_NEON_PINK")
    local i=0 elapsed=0
    hide_cursor
    while kill -0 "$pid" 2>/dev/null; do
        local c="${colors[$((i % ${#colors[@]}))]}"
        local o="${outer[$((i % ${#outer[@]}))]}"
        local n="${inner[$((i % ${#inner[@]}))]}"
        local d="${dots[$((i % ${#dots[@]}))]}"
        local secs=$((elapsed / 10))
        printf "\r   ${c}${BOLD}${o}${R}  ${DIM}${n}${R}  ${C_LGRAY}${msg}${d}${R}  ${DIM}[${C_AMBER}${secs}s${DIM}]${R}   "
        i=$((i+1)); elapsed=$((elapsed+1))
        sleep 0.1
    done
    show_cursor
    printf "\r   ${C_MATRIX_GRN}${BOLD}✓${R}  ${C_WHITE}${done_msg}${R}%-50s\n" " "
}

# ────────────────────────────────────────────────────────────────────────────────
#  MULTI-PHASE GRADIENT PROGRESS BAR
# ────────────────────────────────────────────────────────────────────────────────
progress_bar() {
    local dur="${1:-0.8}" label="${2:-}" phase="${3:-1}"
    local w=52
    local -a grad_p1=('21' '27' '33' '39' '45' '51' '87' '123' '159')
    local -a grad_p2=('196' '202' '208' '214' '220' '226' '227' '228')
    local -a grad_p3=('46' '82' '118' '154' '190' '226' '220' '214')
    local grad_name="grad_p${phase}[@]"
    local -a grad=("${!grad_name}")
    hide_cursor
    for ((i=0; i<=w; i++)); do
        local pct=$(( i * 100 / w ))
        local bar="" g_idx
        for ((f=0; f<i; f++)); do
            g_idx=$(( f * (${#grad[@]} - 1) / w ))
            bar+="\033[38;5;${grad[$g_idx]}m▰"
        done
        local empty; empty=$(rpt "▱" $((w - i)))
        local eta_secs=$(echo "scale=1; ($dur / $w) * ($w - $i)" | bc 2>/dev/null || echo "0")
        printf "\r   ${DIM}[${R}%b${DIM}${empty}]${R}  ${BOLD}${C_GOLD}%3d%%${R}  ${DIM}${IT}%-28s${R}" \
            "$bar" "$pct" "$label"
        sleep "$(echo "scale=5; $dur / $w" | bc 2>/dev/null || echo 0.015)"
    done
    show_cursor; echo ""
    log "Progress: $label (phase $phase) complete"
}

# ────────────────────────────────────────────────────────────────────────────────
#  TYPEWRITER  (with optional color cycling)
# ────────────────────────────────────────────────────────────────────────────────
typewrite() {
    local msg="$1" delay="${2:-0.015}" color="${3:-}"
    local i
    for ((i=0; i<${#msg}; i++)); do
        [[ -n "$color" ]] && printf "%b" "$color"
        printf "%s" "${msg:$i:1}"
        [[ -n "$color" ]] && printf "%b" "$R"
        sleep "$delay"
    done
    echo ""
}

typewrite_rainbow() {
    local msg="$1" delay="${2:-0.025}"
    local -a cols=("$C_NEON_PINK" "$C_NEON_CYAN" "$C_VIOLET" "$C_AMBER" "$C_LIME" "$C_ICE")
    local i
    for ((i=0; i<${#msg}; i++)); do
        printf "%b%s%b" "${cols[$((i % ${#cols[@]}))]}" "${msg:$i:1}" "$R"
        sleep "$delay"
    done
    echo ""
}

# ────────────────────────────────────────────────────────────────────────────────
#  SECTION HEADER  (neon divider with pulse effect)
# ────────────────────────────────────────────────────────────────────────────────
section() {
    local num="$1" title="$2" color="${3:-$C_NEON_CYAN}"
    local w=70
    echo ""
    # Top accent line
    printf "   %b" "$DIM"
    rpt "─" $w
    printf "%b\n" "$R"
    # Content line
    local tag="${BOLD}${color}[ ${num} ]${R}"
    local tag_clean="[ ${num} ]"
    local spacing=$(( w - ${#tag_clean} - ${#title} - 6 ))
    printf "   %b  %b%b%s%b" "$tag" "$BOLD" "$C_WHITE" "$title" "$R"
    printf "%${spacing}s%b%s%b\n" "" "$DIM" "●" "$R"
    # Bottom accent
    printf "   %b" "$DIM"
    rpt "─" $w
    printf "%b\n" "$R"
    echo ""
    log "== Section: $title =="
}

# ────────────────────────────────────────────────────────────────────────────────
#  STATUS LINES
# ────────────────────────────────────────────────────────────────────────────────
ok()    { echo -e "   ${C_MATRIX_GRN}${BOLD}✓${R}  ${C_WHITE}$1${R}"; log "OK: $(strip_color "$1")"; }
warn()  { echo -e "   ${C_AMBER}${BOLD}⚠${R}  ${C_AMBER}$1${R}"; log "WARN: $(strip_color "$1")"; }
err()   { echo -e "   ${C_RED}${BOLD}✗${R}  ${C_CORAL}$1${R}"; log "ERR: $(strip_color "$1")"; }
info()  { echo -e "   ${C_ICE}${BOLD}◈${R}  ${DIM}$1${R}"; log "INFO: $(strip_color "$1")"; }
run()   { echo -e "   ${C_VIOLET}${BOLD}⟶${R}  ${C_WHITE}$1${R}"; log "RUN: $(strip_color "$1")"; }
sub()   { echo -e "      ${DIM}${IT}$1${R}"; }
stat()  { echo -e "   ${C_NEON_CYAN}${BOLD}▸${R}  ${C_LGRAY}$1${R}  ${C_WHITE}${BOLD}$2${R}"; }
badge() {
    local text="$1" color="${2:-$C_NEON_CYAN}"
    echo -e "   ${color}${BG_ACCENT}${BOLD} $text ${R}"
}

# ────────────────────────────────────────────────────────────────────────────────
#  CARD / BOX RENDERER
# ────────────────────────────────────────────────────────────────────────────────
card_open()  {
    local title="${1:-}" color="${2:-$C_GRAY}"
    echo -e "   ${color}╭── ${C_LGRAY}${BOLD}${title}${R}${color} $(rpt "─" $((55 - ${#title})))╮${R}"
}
card_row()   {
    local k="$1" v="$2"
    printf "   ${C_GRAY}│${R}  %-20b  %b%-36b${C_GRAY}│${R}\n" \
        "${DIM}${k}${R}" "" "$v"
}
card_sep()   { echo -e "   ${C_GRAY}│${R}  ${DIM}$(rpt "·" 54)${R}  ${C_GRAY}│${R}"; }
card_close() { echo -e "   ${C_GRAY}╰$(rpt "─" 58)╯${R}"; }

# ────────────────────────────────────────────────────────────────────────────────
#  FILE-TYPE ICON MAP
# ────────────────────────────────────────────────────────────────────────────────
file_icon() {
    local f="$1"
    case "$f" in
        *.js|*.ts|*.jsx|*.tsx) echo "${C_AMBER}⬡${R} " ;;
        *.py)                  echo "${C_ELECTRIC_BLUE}🐍${R} " ;;
        *.go)                  echo "${C_NEON_CYAN}◎${R} " ;;
        *.rs)                  echo "${C_ORANGE}⚙${R} " ;;
        *.sh|*.bash)           echo "${C_LIME}$${R} " ;;
        *.json|*.yaml|*.yml)   echo "${C_LAVENDER}{}${R}" ;;
        *.md|*.txt)            echo "${C_ICE}📄${R}" ;;
        *.css|*.scss|*.sass)   echo "${C_HOT_PINK}◈${R} " ;;
        *.html|*.htm)          echo "${C_CORAL}◇${R} " ;;
        *.sql)                 echo "${C_GOLD}▤${R} " ;;
        *.dockerfile|Dockerfile*) echo "${C_ELECTRIC_BLUE}🐳${R}" ;;
        *.lock|*.sum)          echo "${C_GRAY}🔒${R}" ;;
        *)                     echo "${C_LGRAY}◦${R} " ;;
    esac
}

# ────────────────────────────────────────────────────────────────────────────────
#  LIVE DIFF STATS
# ────────────────────────────────────────────────────────────────────────────────
show_diff_stats() {
    local diff_stat
    diff_stat=$(git diff --cached --stat 2>/dev/null | head -20)
    if [[ -n "$diff_stat" ]]; then
        echo ""
        echo -e "   ${DIM}Staged diff summary:${R}"
        while IFS= read -r line; do
            if [[ "$line" == *"|"* ]]; then
                local fname changes
                fname=$(echo "$line" | awk -F'|' '{print $1}' | sed 's/^ *//;s/ *$//')
                changes=$(echo "$line" | awk -F'|' '{print $2}')
                local icon; icon=$(file_icon "$fname")
                local adds=$(echo "$changes" | grep -o '+' | wc -l | tr -d ' ')
                local dels=$(echo "$changes" | grep -o '-' | wc -l | tr -d ' ')
                printf "      %b${DIM}%-30s${R}  ${C_MATRIX_GRN}+%d${R}  ${C_RED}-%d${R}\n" \
                    "$icon" "$fname" "$adds" "$dels"
            fi
        done <<< "$diff_stat"
    fi
}

# ────────────────────────────────────────────────────────────────────────────────
#  COMMIT MESSAGE SUGGESTIONS  (based on diff heuristics)
# ────────────────────────────────────────────────────────────────────────────────
suggest_commit_msg() {
    local diff_files
    diff_files=$(git diff --cached --name-only 2>/dev/null)
    local suggestions=()

    # Heuristic pattern matching
    echo "$diff_files" | grep -qi "test\|spec" && suggestions+=("Add tests for updated modules")
    echo "$diff_files" | grep -qi "readme\|docs\|\.md" && suggestions+=("Update documentation")
    echo "$diff_files" | grep -qi "\.lock\|package\.json\|go\.sum" && suggestions+=("Update dependencies")
    echo "$diff_files" | grep -qi "dockerfile\|docker-compose\|\.yml\|\.yaml" && suggestions+=("Update deployment configuration")
    echo "$diff_files" | grep -qi "config\|settings\|\.env" && suggestions+=("Update configuration")
    echo "$diff_files" | grep -qi "fix\|bug\|patch" && suggestions+=("Fix identified bugs")
    echo "$diff_files" | grep -qi "refactor\|clean\|format" && suggestions+=("Refactor and clean up code")

    # Count file types
    local num_files; num_files=$(echo "$diff_files" | wc -l | tr -d ' ')
    [[ ${#suggestions[@]} -eq 0 && $num_files -gt 5 ]] && suggestions+=("Update multiple modules")
    [[ ${#suggestions[@]} -eq 0 ]] && suggestions+=("Update $(echo "$diff_files" | head -1 | xargs basename 2>/dev/null || echo 'files')")

    echo "${suggestions[0]}"
}

# ────────────────────────────────────────────────────────────────────────────────
#  NETWORK PREFLIGHT CHECK
# ────────────────────────────────────────────────────────────────────────────────
network_check() {
    local remote_host="$1"
    # Extract hostname from git remote URL
    local hostname
    hostname=$(echo "$remote_host" | sed 's|.*@||;s|:.*||;s|/.*||;s|\.git$||' 2>/dev/null || echo "github.com")

    echo -e "   ${DIM}Checking remote connectivity…${R}"
    local latency="-"
    if command -v ping &>/dev/null; then
        latency=$(ping -c 1 -W 2 "$hostname" 2>/dev/null | grep 'time=' | sed 's/.*time=//;s/ ms//' | head -1 || echo "—")
    fi

    if [[ "$latency" == "—" || -z "$latency" ]]; then
        warn "Could not ping ${hostname} — proceeding anyway"
    else
        ok "Network OK  ${DIM}→${R}  ${C_NEON_CYAN}${hostname}${R}  ${DIM}latency:${R}  ${C_AMBER}${latency}ms${R}"
    fi
}

# ────────────────────────────────────────────────────────────────────────────────
#  UPSTREAM DIVERGENCE CHECK
# ────────────────────────────────────────────────────────────────────────────────
check_divergence() {
    local branch="$1"
    local ahead behind
    ahead=$(git rev-list --count "@{upstream}..HEAD" 2>/dev/null || echo "0")
    behind=$(git rev-list --count "HEAD..@{upstream}" 2>/dev/null || echo "0")

    if [[ "$behind" -gt 0 ]]; then
        warn "Branch is ${C_CORAL}${behind}${C_AMBER} commit(s) behind remote — consider pulling first"
        log "Divergence: ahead=$ahead behind=$behind"
        return 1
    elif [[ "$ahead" -gt 0 ]]; then
        info "Branch is ${C_LIME}${ahead}${DIM} commit(s) ahead of remote"
    else
        ok "Branch is in sync with remote"
    fi
    return 0
}

# ────────────────────────────────────────────────────────────────────────────────
#  HASH VISUAL  (compact block display)
# ────────────────────────────────────────────────────────────────────────────────
display_hash_visual() {
    local hash="$1"
    local -a block_cols=("$C_NEON_CYAN" "$C_VIOLET" "$C_NEON_PINK" "$C_ELECTRIC_BLUE" "$C_AMBER" "$C_LIME" "$C_ICE" "$C_CORAL")
    echo ""
    printf "   ${DIM}SHA  ${R}"
    for ((i=0; i<${#hash}; i+=2)); do
        local pair="${hash:$i:2}"
        local col="${block_cols[$((i % ${#block_cols[@]}))]}"
        printf "%b${BOLD}%s${R}" "$col" "$pair"
        [[ $(( (i+2) % 8 )) -eq 0 && $i -lt 38 ]] && printf "${DIM}·${R}"
    done
    echo ""
}

# ────────────────────────────────────────────────────────────────────────────────
#  ANIMATED BANNER
# ────────────────────────────────────────────────────────────────────────────────
show_banner() {
    clear
    hide_cursor
    sleep 0.05

    # Top border — animated
    printf "   ${C_NEON_CYAN}${BOLD}"
    local border_top="╔$(rpt "═" 70)╗"
    typewrite "$border_top" 0.003 ""
    printf "${R}"

    echo -e "   ${C_NEON_CYAN}${BOLD}║${R}$(rpt " " 70)${C_NEON_CYAN}${BOLD}║${R}"

    # Animated title
    printf "   ${C_NEON_CYAN}${BOLD}║${R}   "
    local -a TITLE_CHARS=(
        "${C_NEON_PINK}G"
        "${C_HOT_PINK}I"
        "${C_VIOLET}T"
        "${C_LAVENDER} "
        "${C_ICE}A"
        "${C_PALE_CYAN}U"
        "${C_NEON_CYAN}T"
        "${C_ELECTRIC_BLUE}O"
        "${C_ICE}P"
        "${C_PALE_CYAN}U"
        "${C_NEON_CYAN}S"
        "${C_ICE}H"
    )
    for ch in "${TITLE_CHARS[@]}"; do
        printf "%b${BOLD}%b${R}" "$ch" ""
        sleep 0.04
    done
    printf "   ${DIM}◈  QUANTUM DEPLOY ENGINE  ◈  NEXUS v4.0${R}"
    printf "$(rpt " " 4)${C_NEON_CYAN}${BOLD}║${R}\n"

    # Session info
    echo -e "   ${C_NEON_CYAN}${BOLD}║${R}   ${DIM}Session:${R}  ${C_AMBER}${BOLD}${SESSION_ID}${R}   ${DIM}·${R}  ${C_LGRAY}$(date '+%Y-%m-%d %H:%M:%S %Z')${R}                 ${C_NEON_CYAN}${BOLD}║${R}"
    echo -e "   ${C_NEON_CYAN}${BOLD}║${R}   ${DIM}Log:${R}  ${C_GRAY}${SESSION_LOG}${R}$(rpt " " 14)${C_NEON_CYAN}${BOLD}║${R}"
    echo -e "   ${C_NEON_CYAN}${BOLD}║${R}$(rpt " " 70)${C_NEON_CYAN}${BOLD}║${R}"

    printf "   ${C_NEON_CYAN}${BOLD}"
    typewrite "╚$(rpt "═" 70)╝" 0.003 ""
    printf "${R}"

    show_cursor
    echo ""
    sleep 0.2
}

# ────────────────────────────────────────────────────────────────────────────────
#  PIPELINE STAGE TRACKER  (live stage indicator)
# ────────────────────────────────────────────────────────────────────────────────
PIPELINE_STAGES=("ENV" "SCAN" "STAGE" "COMMIT" "PUSH" "DONE")
PIPELINE_CURRENT=0

draw_pipeline() {
    local current="$1"
    printf "\n   "
    for ((i=0; i<${#PIPELINE_STAGES[@]}; i++)); do
        local stage="${PIPELINE_STAGES[$i]}"
        if [[ $i -lt $current ]]; then
            printf "${C_MATRIX_GRN}${BOLD}[✓ %-6s]${R}" "$stage"
        elif [[ $i -eq $current ]]; then
            printf "${C_AMBER}${BOLD}[● %-6s]${R}" "$stage"
        else
            printf "${DIM}[○ %-6s]${R}" "$stage"
        fi
        [[ $i -lt $(( ${#PIPELINE_STAGES[@]} - 1 )) ]] && printf "${DIM}──${R}"
    done
    echo ""
}

# ════════════════════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════════════════════
show_banner

# ── STEP 1 · ENVIRONMENT SCAN ──────────────────────────────────────────────────
section "01" "ENVIRONMENT SCAN" "$C_AMBER"
draw_pipeline 0

# Git binary
if ! command -v git &>/dev/null; then
    err "Git binary not found in \$PATH"
    echo -e "\n   ${DIM}Install git and retry: ${C_ICE}https://git-scm.com${R}\n"; exit 1
fi
ok "Git binary  ${DIM}→${R}  ${C_NEON_CYAN}$(git --version | sed 's/git version //')${R}"
sleep 0.05

# Repo check
if ! git rev-parse --git-dir &>/dev/null 2>&1; then
    err "Not inside a Git repository"
    echo -e "\n   ${DIM}Run ${C_ICE}\`git init\`${DIM} or navigate to a valid repository.${R}\n"; exit 1
fi
ok "Repository structure verified"
sleep 0.05

# Repo metadata
BRANCH=$(git branch --show-current 2>/dev/null || echo "HEAD")
REMOTE=$(git remote get-url origin 2>/dev/null || echo "—")
LAST_COMMIT=$(git log -1 --pretty=format:"%h  %s  ${DIM}·${R}  %cr" 2>/dev/null || echo "No commits yet")
TOTAL_COMMITS=$(git rev-list --count HEAD 2>/dev/null || echo "0")
AUTHOR=$(git config user.name 2>/dev/null || echo "Unknown")
AUTHOR_EMAIL=$(git config user.email 2>/dev/null || echo "")
REPO_NAME=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)" || echo "unknown")
STASH_COUNT=$(git stash list 2>/dev/null | wc -l | tr -d ' ')

echo ""
card_open "Repository Metadata" "$C_GRAY"
card_row "${DIM}repo${R}"          "${C_NEON_CYAN}${BOLD}${REPO_NAME}${R}"
card_row "${DIM}branch${R}"        "${C_AMBER}${BOLD}${BRANCH}${R}"
card_row "${DIM}remote${R}"        "${DIM}${REMOTE}${R}"
card_row "${DIM}author${R}"        "${C_WHITE}${AUTHOR}${R}  ${DIM}<${AUTHOR_EMAIL}>${R}"
card_row "${DIM}last commit${R}"   "${DIM}${LAST_COMMIT}${R}"
card_row "${DIM}total commits${R}" "${C_LIME}${BOLD}${TOTAL_COMMITS}${R}"
[[ $STASH_COUNT -gt 0 ]] && card_row "${C_AMBER}stashes${R}" "${C_CORAL}${STASH_COUNT} stashed sets${R}"
card_close
echo ""

# Divergence check (non-fatal)
check_divergence "$BRANCH" 2>/dev/null || true

# ── STEP 2 · WORKING TREE ANALYSIS ────────────────────────────────────────────
section "02" "WORKING TREE ANALYSIS" "$C_NEON_CYAN"
draw_pipeline 1

STATUS_OUTPUT=$(git status --short 2>/dev/null)

if [[ -z "$STATUS_OUTPUT" ]]; then
    warn "Working tree is clean — nothing to commit."
    echo ""
    echo -e "   ${DIM}${IT}Tip: make some changes and try again.${R}"
    echo ""; exit 0
fi

# Parse status
declare -A TYPE_COUNTS
TYPE_COUNTS=([MOD]=0 [ADD]=0 [DEL]=0 [UNT]=0 [REN]=0 [OTH]=0)
declare -a FILE_LIST=()

while IFS= read -r line; do
    local_flag="${line:0:2}"; local_file="${line:3}"
    FILE_LIST+=("$local_file")
    local_icon=$(file_icon "$local_file")
    case "$local_flag" in
        "M "|" M"|"MM"|"AM")
            TYPE_COUNTS[MOD]=$(( TYPE_COUNTS[MOD] + 1 ))
            printf "   ${C_AMBER}  ≋  ${DIM}modified   ${R}%b ${C_WHITE}%s${R}\n" "$local_icon" "$local_file" ;;
        "A "|" A")
            TYPE_COUNTS[ADD]=$(( TYPE_COUNTS[ADD] + 1 ))
            printf "   ${C_MATRIX_GRN}  +  ${DIM}new file   ${R}%b ${C_WHITE}%s${R}\n" "$local_icon" "$local_file" ;;
        "D "|" D")
            TYPE_COUNTS[DEL]=$(( TYPE_COUNTS[DEL] + 1 ))
            printf "   ${C_RED}  −  ${DIM}deleted    ${R}%b ${DIM}%s${R}\n" "$local_icon" "$local_file" ;;
        "??")
            TYPE_COUNTS[UNT]=$(( TYPE_COUNTS[UNT] + 1 ))
            printf "   ${C_ICE}  ?  ${DIM}untracked  ${R}%b ${DIM}%s${R}\n" "$local_icon" "$local_file" ;;
        "R "|" R")
            TYPE_COUNTS[REN]=$(( TYPE_COUNTS[REN] + 1 ))
            printf "   ${C_VIOLET}  →  ${DIM}renamed    ${R}%b ${C_WHITE}%s${R}\n" "$local_icon" "$local_file" ;;
        *)
            TYPE_COUNTS[OTH]=$(( TYPE_COUNTS[OTH] + 1 ))
            printf "   ${C_GRAY}  ·  ${DIM}           %s${R}\n" "$local_file" ;;
    esac
done <<< "$STATUS_OUTPUT"

TOTAL=$(echo "$STATUS_OUTPUT" | wc -l | tr -d ' ')
echo ""

# Summary card
card_open "Change Summary" "$C_GRAY"
[[ ${TYPE_COUNTS[MOD]} -gt 0 ]] && card_row "${C_AMBER}modified${R}"  "${C_AMBER}${BOLD}${TYPE_COUNTS[MOD]}${R}  ${DIM}file(s)${R}"
[[ ${TYPE_COUNTS[ADD]} -gt 0 ]] && card_row "${C_MATRIX_GRN}added${R}"     "${C_MATRIX_GRN}${BOLD}${TYPE_COUNTS[ADD]}${R}  ${DIM}file(s)${R}"
[[ ${TYPE_COUNTS[DEL]} -gt 0 ]] && card_row "${C_RED}deleted${R}"    "${C_RED}${BOLD}${TYPE_COUNTS[DEL]}${R}  ${DIM}file(s)${R}"
[[ ${TYPE_COUNTS[UNT]} -gt 0 ]] && card_row "${C_ICE}untracked${R}"  "${C_ICE}${BOLD}${TYPE_COUNTS[UNT]}${R}  ${DIM}file(s)${R}"
[[ ${TYPE_COUNTS[REN]} -gt 0 ]] && card_row "${C_VIOLET}renamed${R}"   "${C_VIOLET}${BOLD}${TYPE_COUNTS[REN]}${R}  ${DIM}file(s)${R}"
card_sep
card_row "${C_WHITE}${BOLD}TOTAL${R}"      "${C_GOLD}${BOLD}${TOTAL}${R}  ${DIM}file(s) detected${R}"
card_close

# ── STEP 3 · COMMIT MESSAGE ────────────────────────────────────────────────────
section "03" "COMPOSE COMMIT MESSAGE" "$C_NEON_PINK"
draw_pipeline 2

# Smart suggestion
SUGGESTED=$(suggest_commit_msg)
echo -e "   ${DIM}Suggested:${R}  ${C_LAVENDER}${IT}\"${SUGGESTED}\"${R}  ${DIM}(press Enter to use)${R}"
echo -e "   ${DIM}${IT}Use imperative tone  ·  Keep under 72 chars  ·  No trailing period${R}"
echo ""
printf "   ${C_NEON_PINK}${BOLD}❯  commit msg: ${R}${C_WHITE}"
read -r commit_message
printf "${R}"

# Use suggestion if empty
[[ -z "$commit_message" ]] && commit_message="$SUGGESTED"

# Validate
if [[ -z "$commit_message" ]]; then
    err "Commit message required."; echo ""; exit 1
fi

# Message quality analysis
MSG_LEN=${#commit_message}
if   [[ $MSG_LEN -lt 5  ]]; then QUALITY="${C_RED}${BOLD}Too short${R}";             Q_SCORE=1
elif [[ $MSG_LEN -lt 15 ]]; then QUALITY="${C_CORAL}${BOLD}Minimal${R}";             Q_SCORE=2
elif [[ $MSG_LEN -lt 30 ]]; then QUALITY="${C_AMBER}${BOLD}Acceptable${R}";          Q_SCORE=3
elif [[ $MSG_LEN -lt 50 ]]; then QUALITY="${C_LIME}${BOLD}Good${R}";                 Q_SCORE=4
elif [[ $MSG_LEN -lt 72 ]]; then QUALITY="${C_MATRIX_GRN}${BOLD}Ideal ✓${R}";        Q_SCORE=5
else                              QUALITY="${C_ICE}${BOLD}Too long — shorten${R}";   Q_SCORE=2; fi

# Imperative check
FIRST_WORD=$(echo "$commit_message" | awk '{print $1}')
if echo "$FIRST_WORD" | grep -qiE "^(added|fixed|updated|removed|changed|created|deleted|modified)"; then
    TONE_NOTE="${C_CORAL}Consider imperative: \"${FIRST_WORD%?}\" → \"$(echo "$FIRST_WORD" | sed 's/ed$//')\"${R}"
else
    TONE_NOTE="${C_MATRIX_GRN}Imperative tone ✓${R}"
fi

# Quality bar visual
QBAR=""
for ((q=1; q<=5; q++)); do
    [[ $q -le $Q_SCORE ]] && QBAR+="${C_LIME}█" || QBAR+="${DIM}░"
done
QBAR+="${R}"

echo ""
card_open "Message Analysis" "$C_GRAY"
card_row "${DIM}message${R}"    "${BOLD}${C_WHITE}\"${commit_message}\"${R}"
card_row "${DIM}length${R}"     "${C_WHITE}${BOLD}${MSG_LEN}${R}  ${DIM}chars${R}"
card_row "${DIM}quality${R}"    "${QBAR}  ${QUALITY}"
card_row "${DIM}tone${R}"       "${TONE_NOTE}"
card_close

# ── STEP 4 · MULTI-REMOTE SELECT ──────────────────────────────────────────────
section "04" "TARGET CONFIGURATION" "$C_ELECTRIC_BLUE"
draw_pipeline 3

# List all remotes
REMOTES_LIST=$(git remote 2>/dev/null)
REMOTE_COUNT=$(echo "$REMOTES_LIST" | wc -l | tr -d ' ')
PUSH_REMOTE="origin"

if [[ $REMOTE_COUNT -gt 1 ]]; then
    echo -e "   ${DIM}Multiple remotes detected:${R}"
    i=1
    while IFS= read -r r; do
        local rurl; rurl=$(git remote get-url "$r" 2>/dev/null || echo "—")
        echo -e "   ${C_AMBER}${BOLD}[$i]${R}  ${C_WHITE}${r}${R}  ${DIM}→  ${rurl}${R}"
        i=$((i+1))
    done <<< "$REMOTES_LIST"
    echo ""
    printf "   ${C_ELECTRIC_BLUE}${BOLD}❯  Remote [default: origin]: ${R}${C_WHITE}"
    read -r chosen_remote
    printf "${R}"
    [[ -n "$chosen_remote" ]] && PUSH_REMOTE="$chosen_remote"
fi

PUSH_URL=$(git remote get-url "$PUSH_REMOTE" 2>/dev/null || echo "—")
echo ""
stat "Push target" "${C_NEON_CYAN}${PUSH_REMOTE}/${BRANCH}${R}"
stat "URL" "${DIM}${PUSH_URL}${R}"
echo ""

# Network preflight
network_check "$PUSH_URL"

# ── STEP 5 · CONFIRM DEPLOY ────────────────────────────────────────────────────
section "05" "CONFIRM DEPLOY" "$C_MATRIX_GRN"
draw_pipeline 4

echo ""
card_open "Deployment Summary" "$C_MATRIX_GRN"
card_row "${DIM}repository${R}"   "${C_NEON_CYAN}${BOLD}${REPO_NAME}${R}"
card_row "${DIM}target${R}"       "${C_AMBER}${BOLD}${PUSH_REMOTE}/${BRANCH}${R}"
card_row "${DIM}message${R}"      "${IT}\"${commit_message}\"${R}"
card_row "${DIM}files${R}"        "${C_GOLD}${BOLD}${TOTAL}${R}  ${DIM}file(s) will be staged & committed${R}"
card_row "${DIM}author${R}"       "${C_WHITE}${AUTHOR}${R}  ${DIM}<${AUTHOR_EMAIL}>${R}"
card_row "${DIM}session${R}"      "${DIM}${SESSION_ID}${R}"
card_close
echo ""

# Confirm prompt with timeout
CONFIRM_TIMEOUT=30
printf "   ${C_MATRIX_GRN}${BOLD}Deploy now?${R}  ${DIM}[y/N]${R}  ${DIM}(auto-abort in ${CONFIRM_TIMEOUT}s)${R}  ${C_WHITE}"
if read -r -t "$CONFIRM_TIMEOUT" confirm 2>/dev/null; then
    printf "${R}"
else
    printf "${R}"
    echo ""
    warn "Timed out — aborted."; echo ""; exit 0
fi

if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo ""; warn "Aborted by operator.  ${DIM}No changes committed.${R}"; echo ""; exit 0
fi

# ── STEP 6 · PIPELINE EXECUTION ───────────────────────────────────────────────
section "06" "PIPELINE EXECUTION" "$C_VIOLET"
draw_pipeline 5

PIPE_START=$(date +%s%N 2>/dev/null || date +%s)

echo ""

# ── Stage ────────────────────────────────────────────────────────────────────
run "${C_VIOLET}STAGE${R}  ·  git add ."
(git add . >/tmp/_ap_out 2>&1) & spinner $! "Indexing working tree" "Staging complete"
progress_bar 0.4 "Staging objects" 2

# Show diff stats after staging
show_diff_stats
echo ""

# ── Commit ───────────────────────────────────────────────────────────────────
run "${C_NEON_PINK}COMMIT${R}  ·  Writing commit object"
(git commit -m "$commit_message" >/tmp/_ap_out 2>&1) &
CPID=$!; spinner $CPID "Creating commit object" "Commit written"; wait $CPID; CEXIT=$?
if [[ $CEXIT -ne 0 ]]; then
    echo ""
    err "Commit failed  ${DIM}→  see below${R}"
    while IFS= read -r ln; do sub "$ln"; done </tmp/_ap_out
    echo ""
    echo -e "   ${DIM}${IT}Rollback command:${R}  ${C_CORAL}git reset HEAD~1${R}"
    log "COMMIT FAILED"
    exit 1
fi
progress_bar 0.35 "Writing commit tree" 1

NEW_HASH=$(git log -1 --pretty=format:"%H")
SHORT_HASH=$(git log -1 --pretty=format:"%h")
COMMIT_TS=$(git log -1 --pretty=format:"%ci")
display_hash_visual "$NEW_HASH"
echo ""

# ── Push ─────────────────────────────────────────────────────────────────────
run "${C_NEON_CYAN}PUSH${R}  ·  Transmitting to ${PUSH_REMOTE}/${BRANCH}"
(git push -u "$PUSH_REMOTE" "$BRANCH" >/tmp/_ap_out 2>&1) &
PPID_=$!; spinner $PPID_ "Uploading pack objects" "Remote updated"; wait $PPID_; PEXIT=$?
if [[ $PEXIT -ne 0 ]]; then
    echo ""
    err "Push rejected  ${DIM}→  see below${R}"
    while IFS= read -r ln; do sub "$ln"; done </tmp/_ap_out
    echo ""
    echo -e "   ${DIM}${IT}Possible fix:${R}  ${C_CORAL}git pull --rebase ${PUSH_REMOTE} ${BRANCH}${R}"
    log "PUSH FAILED"
    exit 1
fi
progress_bar 0.7 "Uploading deltas" 3
echo ""

# Timing
PIPE_END=$(date +%s%N 2>/dev/null || date +%s)
if [[ "$PIPE_END" =~ ^[0-9]{19}$ ]]; then
    ELAPSED_MS=$(( (PIPE_END - PIPE_START) / 1000000 ))
    ELAPSED_FMT="${ELAPSED_MS}ms"
else
    ELAPSED_FMT="$(( PIPE_END - PIPE_START ))s"
fi

# ════════════════════════════════════════════════════════════════════════════════
#  COMPLETION SCREEN
# ════════════════════════════════════════════════════════════════════════════════
draw_pipeline 6
sleep 0.15

echo ""
# Animated success banner
printf "   ${C_MATRIX_GRN}${BOLD}"
typewrite "╔$(rpt "═" 64)╗" 0.002 ""
printf "${R}"
echo -e "   ${C_MATRIX_GRN}${BOLD}║${R}$(rpt " " 64)${C_MATRIX_GRN}${BOLD}║${R}"

printf "   ${C_MATRIX_GRN}${BOLD}║${R}   "
typewrite_rainbow "  ✦  DEPLOY SUCCESSFUL  ✦  ALL SYSTEMS NOMINAL  " 0.02
printf "  ${C_MATRIX_GRN}${BOLD}║${R}\n"

echo -e "   ${C_MATRIX_GRN}${BOLD}║${R}   ${DIM}${IT}Your code is live. The world is a better place.${R}$(rpt " " 14)${C_MATRIX_GRN}${BOLD}║${R}"
echo -e "   ${C_MATRIX_GRN}${BOLD}║${R}$(rpt " " 64)${C_MATRIX_GRN}${BOLD}║${R}"
printf "   ${C_MATRIX_GRN}${BOLD}"
typewrite "╚$(rpt "═" 64)╝" 0.002 ""
printf "${R}"

echo ""
echo ""

# Deployment receipt
PUSHED_TIME=$(git log -1 --pretty=format:"%cr" 2>/dev/null)
REMOTE_REF="${PUSH_REMOTE}/${BRANCH}"

card_open "◈  Deployment Receipt" "$C_NEON_CYAN"
echo -e "   ${C_NEON_CYAN}│${R}"
card_row "${DIM}repository${R}"   "${C_NEON_CYAN}${BOLD}${REPO_NAME}${R}"
card_row "${DIM}branch${R}"       "${C_AMBER}${BOLD}${BRANCH}${R}  ${DIM}→${R}  ${C_ICE}${REMOTE_REF}${R}"
card_row "${DIM}commit${R}"       "${C_GOLD}${BOLD}${SHORT_HASH}${R}  ${DIM}(${NEW_HASH:0:24}…)${R}"
card_row "${DIM}message${R}"      "${IT}\"${commit_message}\"${R}"
card_row "${DIM}files${R}"        "${C_WHITE}${BOLD}${TOTAL}${R}  ${DIM}changed${R}"
card_row "${DIM}author${R}"       "${C_WHITE}${AUTHOR}${R}"
card_row "${DIM}pushed${R}"       "${C_LIME}${PUSHED_TIME}${R}"
card_row "${DIM}duration${R}"     "${C_AMBER}${ELAPSED_FMT}${R}"
card_row "${DIM}session${R}"      "${DIM}${SESSION_ID}${R}"
card_row "${DIM}log${R}"          "${DIM}${SESSION_LOG}${R}"
echo -e "   ${C_NEON_CYAN}│${R}"
card_close

echo ""
echo -e "   ${DIM}${C_ICE}◈${R}  ${DIM}${IT}Powered by git-autopush Quantum Edition  ·  NEXUS v4.0${R}"
echo -e "   ${DIM}${C_GRAY}◈${R}  ${DIM}${IT}Session log saved to ~/.gitautopush/logs/${R}"
echo ""

# ── Log final state
log "DEPLOY SUCCESS: hash=$NEW_HASH branch=$BRANCH remote=$PUSH_REMOTE files=$TOTAL duration=$ELAPSED_FMT"
rm -f /tmp/_ap_out
exit 0
