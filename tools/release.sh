#!/bin/bash
# Publish a PsychInterview release after the tests pass. Run from anywhere.
# usage: APP=<clone of main> DT=<dev-tools worktree> SESSION=<claude session url> release.sh "<main commit subject>" "<body>" "<dev-tools commit subject>"
# Refuses to push if main moved since the last fetch (another chat released): rebase, renumber cache + What's new, rerun tests, try again.
set -e
APP=${APP:-$PWD}; DT=${DT:-$APP/../dt}
TAIL="Co-Authored-By: Claude <noreply@anthropic.com>${SESSION:+
Claude-Session: $SESSION}"
cd "$APP"
git add -A && git commit -q -m "$1

$2

$TAIL"
git fetch -q origin main
if ! git merge-base --is-ancestor origin/main HEAD; then echo "MAIN MOVED: rebase needed"; git log --oneline -3 origin/main; exit 3; fi
git push origin HEAD:main 2>&1 | tail -1
cd "$DT" && git add -A && git commit -q -m "$3

$TAIL" && git push origin HEAD:dev-tools 2>&1 | tail -1
git -C "$APP" log --oneline -1
