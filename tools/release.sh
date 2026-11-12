#!/bin/bash
# usage: release.sh "<main subject>" "<body>" "<dev-tools subject>"
set -e
APP=${APP:-/home/claude/work/case-psychinterview}; DT=${DT:-/home/claude/work/dt}
TAIL="Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>
${SESSION:+Claude-Session: $SESSION}"
cd "$APP"; git add -A
if git log -1 --format=%s | grep -q '^wip$'; then git commit -q --amend -m "$1

$2

$TAIL"; else git commit -q -m "$1

$2

$TAIL"; fi
git fetch -q origin main
if ! git merge-base --is-ancestor origin/main HEAD; then echo "MAIN MOVED: rebase needed"; git log --oneline -3 origin/main; exit 3; fi
git push origin HEAD:main 2>&1 | tail -1
cd "$DT"; git add -A; git commit -q -m "$3

$TAIL"; git fetch -q origin dev-tools; git merge-base --is-ancestor origin/dev-tools HEAD || git rebase -q origin/dev-tools; git push origin HEAD:dev-tools 2>&1 | tail -1
git -C "$APP" log --oneline -1
