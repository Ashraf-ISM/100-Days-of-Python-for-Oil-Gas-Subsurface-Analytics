#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                   GIT AUTOPUSH  ·  HYPER DEPLOY ENGINE                  ║
# ║                   v3.0 · Quantum Edition · by autopush                   ║
# ╚══════════════════════════════════════════════════════════════════════════╝

# ── Palette ────────────────────────────────────────────────────────────────
R='\033[0m'
BOLD='\033[1m'; DIM='\033[2m'; IT='\033[3m'; UL='\033[4m'

# Standard
BLK='\033[30m'; RED='\033[31m'; GRN='\033[32m'; YLW='\033[33m'
BLU='\033[34m'; MAG='\033[35m'; CYN='\033[36m'; WHT='\033[37m'

# Bright
bRED='\033[91m'; bGRN='\033[92m'; bYLW='\033[93m'
bBLU='\033[94m'; bMAG='\033[95m'; bCYN='\033[96m'; bWHT='\033[97m'

# Backgrounds
BG0='\033[40m'; BG1='\033[48;5;234m'; BG2='\033[48;5;236m'

# 256-color extras (neon palette)
N1='\033[38;5;51m'   # electric cyan
N2='\033[38;5;129m'  # violet
N3='\033[38;5;201m'  # neon pink
N4='\033[38;5;46m'   # matrix green
N5='\033[38;5;220m'  # amber
N6='\033[38;5;87m'   # ice blue
N7='\033[38;5;226m'  # yellow-white
N8='\033[38;5;213m'  # hot pink
N9='\033[38;5;159m'  # pale cyan


# ── Utilities ──────────────────────────────────────────────────────────────
hide_cursor() { tput civis 2>/dev/null; }
show_cursor() { tput cnorm 2>/dev/null; }
trap 'show_cursor; echo ""' EXIT INT TERM

pad()  { printf "%-${1}s" "$2"; }
rpt()  { printf '%0.s'"$1" $(seq 1 "$2"); }

# ── Spinner (dual-ring) ────────────────────────────────────────────────────
spinner() {
    local pid=$1 msg="${2:-Processing…}"
    local outer=('◜' '◝' '◞' '◟') inner=('·' '·' '·' ' ')
    local pal=("$N1" "$N6" "$N9" "$N2" "$N3" "$bMAG")
    local i=0
    hide_cursor
    while kill -0 "$pid" 2>/dev/null; do
        local c=${pal[$((i % ${#pal[@]}))]}
        local o=${outer[$((i % 4))]}
        printf "\r   ${c}${BOLD}${o}${R}  ${DIM}${msg}${R}   "
        i=$((i+1)); sleep 0.07
    done
    show_cursor
    printf "\r%-70s\r" " "
}

# ── Gradient progress bar ──────────────────────────────────────────────────
progress_bar() {
    local dur=${1:-0.6} label="${2:-}" w=50
    local grad=("\033[38;5;21m" "\033[38;5;27m" "\033[38;5;33m" "\033[38;5;39m" "\033[38;5;45m" "\033[38;5;51m" "\033[38;5;87m" "\033[38;5;123m")
    hide_cursor
    for ((i=0; i<=w; i++)); do
        local pct=$(( i * 100 / w ))
        local bar="" g_idx
        for ((f=0; f<i; f++)); do
            g_idx=$(( f * ${#grad[@]} / w ))
            bar+="${grad[$g_idx]}▰"
        done
        local empty; empty=$(rpt "▱" $((w - i)))
        printf "\r   ${DIM}[${R}${bar}${DIM}${empty}]${R}  ${BOLD}${N7}%3d%%${R}  ${DIM}${IT}${label}${R}" "$pct"
        sleep "$(echo "scale=4; $dur / $w" | bc 2>/dev/null || echo 0.012)"
    done
    show_cursor; echo ""
}

# ── Typewriter ─────────────────────────────────────────────────────────────
typewrite() {
    local msg="$1" delay="${2:-0.018}"
    local i; for ((i=0; i<${#msg}; i++)); do printf "%s" "${msg:$i:1}"; sleep "$delay"; done; echo ""
}

# ── Section header ─────────────────────────────────────────────────────────
section() {
    local title="$1" color="${2:-$N1}"
    local w=66 tlen=${#title} pad_total line
    pad_total=$(( (w - tlen - 2) ))
    local left=$(( pad_total / 2 )) right=$(( pad_total - pad_total / 2 ))
    local lpad; lpad=$(rpt "─" "$left")
    local rpad; rpad=$(rpt "─" "$right")
    echo ""
    echo -e "   ${DIM}${lpad}${R}  ${color}${BOLD}${title}${R}  ${DIM}${rpad}${R}"
    echo ""
}

# ── Status lines ───────────────────────────────────────────────────────────
ok()   { echo -e "   ${N4}${BOLD}✓${R}  ${bWHT}$1${R}"; }
warn() { echo -e "   ${N5}${BOLD}△${R}  ${YLW}$1${R}"; }
err()  { echo -e "   ${bRED}${BOLD}✗${R}  ${RED}$1${R}"; }
info() { echo -e "   ${N6}${BOLD}·${R}  ${DIM}$1${R}"; }
run()  { echo -e "   ${N2}${BOLD}⟶${R}  ${WHT}$1${R}"; }
sub()  { echo -e "   ${DIM}   ${IT}$1${R}"; }

# ══════════════════════════════════════════════════════════════════════════
#  BANNER
# ══════════════════════════════════════════════════════════════════════════
clear; sleep 0.05

echo ""
echo -e "${N1}${BOLD}   ┌──────────────────────────────────────────────────────────────┐${R}"
echo -e "${N1}${BOLD}   │${R}                                                              ${N1}${BOLD}│${R}"

printf "${N1}${BOLD}   │${R}   "
# Animated paint of title line
title_parts=(
  "${N3}${BOLD}G" "${bMAG}I" "${N2}T" "${R}${DIM} " 
  "${N1}${BOLD}A" "${N6}U" "${N9}T" "${N1}O" "${bCYN}P" "${N6}U" "${N8}S" "${N1}H"
)
for part in "${title_parts[@]}"; do printf "${part}"; sleep 0.035; done
printf "${R}"
printf "   ${DIM}${IT}Quantum Deploy Engine${R}"
echo -e "                    ${N1}${BOLD}│${R}"

echo -e "${N1}${BOLD}   │${R}   ${DIM}v3.0  ·  Hyper Edition  ·  $(date '+%Y-%m-%d %H:%M:%S')${R}                    ${N1}${BOLD}│${R}"
echo -e "${N1}${BOLD}   │${R}                                                              ${N1}${BOLD}│${R}"
echo -e "${N1}${BOLD}   └──────────────────────────────────────────────────────────────┘${R}"
echo ""
sleep 0.2

# ══════════════════════════════════════════════════════════════════════════
#  STEP 1 — ENVIRONMENT SCAN
# ══════════════════════════════════════════════════════════════════════════
section "01  ENVIRONMENT SCAN" "$N5"

sleep 0.05
if ! command -v git &>/dev/null; then
    err "Git binary not found in \$PATH"
    echo -e "\n   ${DIM}Install git and retry.${R}\n"; exit 1
fi
ok "Git binary  ${DIM}→${R}  ${N4}$(git --version | sed 's/git version //')"
sleep 0.05

if ! git rev-parse --git-dir &>/dev/null 2>&1; then
    err "Not inside a Git repository"
    echo -e "\n   ${DIM}Run \`git init\` or navigate to a repo.${R}\n"; exit 1
fi
ok "Repository structure verified"
sleep 0.05

BRANCH=$(git branch --show-current 2>/dev/null || echo "HEAD")
REMOTE=$(git remote get-url origin 2>/dev/null || echo "—")
LAST_COMMIT=$(git log -1 --pretty=format:"%h  %s" 2>/dev/null || echo "No commits yet")
TOTAL_COMMITS=$(git rev-list --count HEAD 2>/dev/null || echo "0")
AUTHOR=$(git config user.name 2>/dev/null || echo "Unknown")

info "Branch       ${bWHT}${BRANCH}${R}"
info "Remote       ${bWHT}${REMOTE}${R}"
info "Last commit  ${DIM}${LAST_COMMIT}${R}"
info "Total        ${bWHT}${TOTAL_COMMITS}${R} commits  ·  author: ${bWHT}${AUTHOR}${R}"

# ══════════════════════════════════════════════════════════════════════════
#  STEP 2 — WORKING TREE ANALYSIS
# ══════════════════════════════════════════════════════════════════════════
section "02  WORKING TREE ANALYSIS" "$N1"

STATUS_OUTPUT=$(git status --short 2>/dev/null)

if [[ -z "$STATUS_OUTPUT" ]]; then
    warn "Working tree is clean — nothing to stage."
    echo ""
    echo -e "   ${DIM}${IT}Nothing to push. Exiting gracefully.${R}"
    echo ""; exit 0
fi

# Counters
MOD=0; ADD=0; DEL=0; UNT=0; REN=0; OTH=0

while IFS= read -r line; do
    flag="${line:0:2}"; file="${line:3}"
    case "$flag" in
        "M "|" M"|"MM") ((MOD++)); echo -e "   ${N5}  ≋  ${DIM}modified   ${R}${bWHT}${file}${R}" ;;
        "A "|" A")       ((ADD++)); echo -e "   ${N4}  +  ${DIM}new file   ${R}${bWHT}${file}${R}" ;;
        "D "|" D")       ((DEL++)); echo -e "   ${bRED}  −  ${DIM}deleted    ${R}${DIM}${file}${R}" ;;
        "??")            ((UNT++)); echo -e "   ${N6}  ?  ${DIM}untracked  ${R}${DIM}${file}${R}" ;;
        "R "|" R")       ((REN++)); echo -e "   ${N2}  →  ${DIM}renamed    ${R}${bWHT}${file}${R}" ;;
        *)               ((OTH++)); echo -e "   ${DIM}  ·           ${file}${R}" ;;
    esac
done <<< "$STATUS_OUTPUT"

TOTAL=$(echo "$STATUS_OUTPUT" | wc -l | tr -d ' ')
echo ""
echo -e "   ${DIM}┌─────────────────────────────────────┐${R}"
[[ $MOD -gt 0 ]] && echo -e "   ${DIM}│${R}  ${N5}modified${R}   ${DIM}·${R}  ${BOLD}${bWHT}${MOD}${R}                       ${DIM}│${R}"
[[ $ADD -gt 0 ]] && echo -e "   ${DIM}│${R}  ${N4}added${R}      ${DIM}·${R}  ${BOLD}${bWHT}${ADD}${R}                       ${DIM}│${R}"
[[ $DEL -gt 0 ]] && echo -e "   ${DIM}│${R}  ${bRED}deleted${R}    ${DIM}·${R}  ${BOLD}${bWHT}${DEL}${R}                       ${DIM}│${R}"
[[ $UNT -gt 0 ]] && echo -e "   ${DIM}│${R}  ${N6}untracked${R}  ${DIM}·${R}  ${BOLD}${bWHT}${UNT}${R}                       ${DIM}│${R}"
[[ $REN -gt 0 ]] && echo -e "   ${DIM}│${R}  ${N2}renamed${R}    ${DIM}·${R}  ${BOLD}${bWHT}${REN}${R}                       ${DIM}│${R}"
echo -e "   ${DIM}│${R}  ${DIM}──────────────────────${R}               ${DIM}│${R}"
echo -e "   ${DIM}│${R}  ${N9}total${R}      ${DIM}·${R}  ${BOLD}${bWHT}${TOTAL}${R} file(s) staged         ${DIM}│${R}"
echo -e "   ${DIM}└─────────────────────────────────────┘${R}"

# ══════════════════════════════════════════════════════════════════════════
#  STEP 3 — COMMIT MESSAGE
# ══════════════════════════════════════════════════════════════════════════
section "03  COMPOSE COMMIT MESSAGE" "$N3"

echo -e "   ${DIM}${IT}Use imperative tone: \"Add auth module\", \"Fix null pointer\", \"Refactor DB layer\"${R}"
echo ""
printf "   ${N3}${BOLD}❯  ${R}${bWHT}"
read -r commit_message
printf "${R}"

if [[ -z "$commit_message" ]]; then
    echo ""; err "Commit message is required."; echo ""; exit 1
fi

# Smart tag detection
MSG_LEN=${#commit_message}
if [[ $MSG_LEN -lt 10 ]]; then   QUALITY="${bRED}Too short${R}"
elif [[ $MSG_LEN -lt 30 ]]; then  QUALITY="${N5}OK${R}"
elif [[ $MSG_LEN -lt 72 ]]; then  QUALITY="${N4}Ideal${R}"
else                              QUALITY="${N6}Long — consider shortening${R}"
fi

echo ""
echo -e "   ${DIM}┌── Message Preview ────────────────────────────────────┐${R}"
echo -e "   ${DIM}│${R}"
echo -e "   ${DIM}│${R}   ${BOLD}${bWHT}\"${commit_message}\"${R}"
echo -e "   ${DIM}│${R}"
echo -e "   ${DIM}│${R}   ${DIM}Length${R}   ${BOLD}${bWHT}${MSG_LEN}${R} chars  ·  Quality  ${QUALITY}"
echo -e "   ${DIM}└───────────────────────────────────────────────────────┘${R}"

# ══════════════════════════════════════════════════════════════════════════
#  STEP 4 — CONFIRM
# ══════════════════════════════════════════════════════════════════════════
section "04  CONFIRM DEPLOY" "$N4"

echo -e "   ${DIM}Target  ${R}  ${BOLD}${N1}origin/${BRANCH}${R}"
echo -e "   ${DIM}Message ${R}  ${IT}\"${commit_message}\"${R}"
echo -e "   ${DIM}Files   ${R}  ${BOLD}${bWHT}${TOTAL}${R} file(s)"
echo -e "   ${DIM}Author  ${R}  ${bWHT}${AUTHOR}${R}"
echo ""
printf "   ${N4}${BOLD}Deploy now?${R}  ${DIM}[y/N]${R}  ${bWHT}"
read -r confirm
printf "${R}"

if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo ""; warn "Aborted by operator.  ${DIM}No changes committed.${R}"; echo ""; exit 0
fi

# ══════════════════════════════════════════════════════════════════════════
#  STEP 5 — PIPELINE EXECUTION
# ══════════════════════════════════════════════════════════════════════════
section "05  PIPELINE EXECUTION" "$N2"

PIPE_START=$(date +%s)

# ── Stage ──
run "git add  ·  staging all changes"
(git add . >/tmp/_ap_out 2>&1) & spinner $! "Indexing working tree…"
progress_bar 0.5 "Staging objects"
ok "Working tree staged"
echo ""

# ── Commit ──
run "git commit  ·  writing object"
(git commit -m "$commit_message" >/tmp/_ap_out 2>&1) &
CPID=$!; spinner $CPID "Creating commit object…"; wait $CPID; CEXIT=$?
if [[ $CEXIT -ne 0 ]]; then
    err "Commit failed:"; while IFS= read -r ln; do sub "$ln"; done </tmp/_ap_out
    echo ""; exit 1
fi
progress_bar 0.45 "Writing commit"
ok "Commit object written"
NEW_HASH=$(git log -1 --pretty=format:"%H")
SHORT_HASH=$(git log -1 --pretty=format:"%h")
sub "${DIM}sha1  ${N6}${NEW_HASH}${R}"
echo ""

# ── Push ──
run "git push  ·  uploading to origin/${BRANCH}"
(git push -u origin "$BRANCH" >/tmp/_ap_out 2>&1) &
PPID_=$!; spinner $PPID_ "Transmitting to remote…"; wait $PPID_; PEXIT=$?
if [[ $PEXIT -ne 0 ]]; then
    err "Push rejected:"; while IFS= read -r ln; do sub "$ln"; done </tmp/_ap_out
    echo ""; exit 1
fi
progress_bar 0.8 "Uploading pack objects"
ok "Remote updated"
echo ""

PIPE_END=$(date +%s)
ELAPSED=$(( PIPE_END - PIPE_START ))

# ══════════════════════════════════════════════════════════════════════════
#  COMPLETION SCREEN
# ══════════════════════════════════════════════════════════════════════════
sleep 0.15
echo ""
echo -e "${N4}${BOLD}   ╔══════════════════════════════════════════════════════════════╗${R}"
echo -e "${N4}${BOLD}   ║${R}                                                              ${N4}${BOLD}║${R}"
echo -e "${N4}${BOLD}   ║${R}   ${N4}${BOLD}DEPLOY SUCCESSFUL${R}                                          ${N4}${BOLD}║${R}"
echo -e "${N4}${BOLD}   ║${R}   ${DIM}${IT}All systems nominal. Your code is in the wild.${R}             ${N4}${BOLD}║${R}"
echo -e "${N4}${BOLD}   ║${R}                                                              ${N4}${BOLD}║${R}"
echo -e "${N4}${BOLD}   ╚══════════════════════════════════════════════════════════════╝${R}"
echo ""

PUSHED_TIME=$(git log -1 --pretty=format:"%cr" 2>/dev/null)

echo -e "   ${DIM}┌── Deployment Record ──────────────────────────────────┐${R}"
echo -e "   ${DIM}│${R}"
echo -e "   ${DIM}│${R}   ${DIM}branch     ${R}${BOLD}${N1}${BRANCH}${R}"
echo -e "   ${DIM}│${R}   ${DIM}commit     ${R}${BOLD}${N5}${SHORT_HASH}${R}  ${DIM}(${NEW_HASH:0:20}…)${R}"
echo -e "   ${DIM}│${R}   ${DIM}message    ${R}${IT}\"${commit_message}\"${R}"
echo -e "   ${DIM}│${R}   ${DIM}files      ${R}${BOLD}${bWHT}${TOTAL}${R} changed"
echo -e "   ${DIM}│${R}   ${DIM}pushed     ${R}${bWHT}${PUSHED_TIME}${R}"
echo -e "   ${DIM}│${R}   ${DIM}duration   ${R}${bWHT}${ELAPSED}s${R}"
echo -e "   ${DIM}│${R}"
echo -e "   ${DIM}└───────────────────────────────────────────────────────┘${R}"
echo ""
echo -e "   ${DIM}${N6}◈${R}  ${DIM}${IT}Powered by git-autopush Quantum Edition${R}"
echo ""

rm -f /tmp/_ap_out
exit 0