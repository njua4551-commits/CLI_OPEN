#!/usr/bin/env bash
# Verify the complete CI change range, including whitespace introduced before the tip.
set -euo pipefail

case "${EVENT_NAME:?Missing CI event}" in
  pull_request)
    head=${PR_HEAD_SHA:?Missing pull request head}
    base=$(git merge-base "${PR_BASE_SHA:?Missing pull request base}" "$head")
    ;;
  push)
    head=HEAD
    base=${PUSH_BEFORE:?Missing push base}
    if [[ $base =~ ^0+$ ]]; then
      default_ref="refs/remotes/origin/${DEFAULT_BRANCH:?Missing default branch}"
      if git show-ref --verify --quiet "$default_ref" &&
          [[ $(git rev-parse "$default_ref") != "$(git rev-parse "$head")" ]]; then
        base=$(git merge-base "$default_ref" "$head") || {
          echo "Cannot determine the initial branch change range" >&2
          exit 1
        }
      else
        base=$(git hash-object -w -t tree /dev/null)
      fi
    else
      git cat-file -e "$base^{commit}" || {
        echo "Push base is unavailable. Fetch the event SHA or restore the missing history." >&2
        exit 1
      }
    fi
    ;;
  *)
    echo "Unsupported CI event: $EVENT_NAME" >&2
    exit 1
    ;;
esac

git diff --check "$base" "$head" --
