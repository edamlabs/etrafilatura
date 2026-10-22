#!/usr/bin/env bash
# Public API and release notes of an upstream crate between two published versions.
# usage: tools/apidiff.sh <crate> <old> <new> <owner/repo> <outdir>
set -euo pipefail

CRATE="$1" OLD="$2" NEW="$3" REPO="$4" OUT="$5"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$OUT"

api() {
    curl -sSfL "https://static.crates.io/crates/$CRATE/$CRATE-$1.crate" | tar xz -C "$WORK"
    cargo +nightly public-api --manifest-path "$WORK/$CRATE-$1/Cargo.toml" -sss 2>/dev/null | sort > "$WORK/api-$1.txt"
}

echo "$OLD -> $NEW" > "$OUT/versions.txt"
api "$OLD"
api "$NEW"
diff -u "$WORK/api-$OLD.txt" "$WORK/api-$NEW.txt" > "$OUT/api-diff.txt" || true
comm -13 "$WORK/api-$OLD.txt" "$WORK/api-$NEW.txt" > "$OUT/api-added.txt"
comm -23 "$WORK/api-$OLD.txt" "$WORK/api-$NEW.txt" > "$OUT/api-removed.txt"
gh release view "v$NEW" -R "$REPO" --json body -q .body > "$OUT/release-notes.md" 2>/dev/null \
    || echo "(no GitHub release notes for v$NEW)" > "$OUT/release-notes.md"
wc -l "$OUT"/api-added.txt "$OUT"/api-removed.txt
