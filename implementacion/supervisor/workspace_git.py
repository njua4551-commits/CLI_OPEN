"""Publish an approved review to a separate ref using one Git transaction."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

GIT = "/usr/bin/git"
ENV = {
    "PATH": "/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_TERMINAL_PROMPT": "0", "GIT_NO_REPLACE_OBJECTS": "1",
    "GIT_AUTHOR_NAME": "CLI_OPEN", "GIT_AUTHOR_EMAIL": "cli-open@localhost",
    "GIT_COMMITTER_NAME": "CLI_OPEN", "GIT_COMMITTER_EMAIL": "cli-open@localhost",
}
OID = re.compile(r"(?:[a-f0-9]{40}|[a-f0-9]{64})")


def git(root, *args, index=None, data=None):
    env = dict(ENV)
    if index is not None:
        env["GIT_INDEX_FILE"] = str(index)
    return subprocess.run(
        [GIT, "--no-optional-locks", "-c", "core.hooksPath=/dev/null",
         "-c", "core.fsmonitor=false", "-C", str(root), *args],
        env=env, input=data, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10, check=True,
    ).stdout


def base_commit(root):
    try:
        actual = Path(os.fsdecode(git(root, "rev-parse", "--show-toplevel").rstrip(b"\n")))
        if actual != root:
            return None
        value = git(root, "rev-parse", "--verify", "HEAD^{commit}").decode("ascii").strip()
        return value if OID.fullmatch(value) else None
    except (OSError, subprocess.SubprocessError):
        return None


def approval(root, base, changes, edits):
    data = json.dumps([str(root), base, changes, edits], ensure_ascii=True, sort_keys=True)
    return hashlib.sha256(data.encode("ascii")).hexdigest()


def check_base(root, base, changes):
    for change in changes:
        name = change["path"]
        tree = git(root, "ls-tree", "-z", base, "--", name)
        staged = git(root, "ls-files", "--stage", "-z", "--", name)
        if not tree and not staged and change["operation"] == "create":
            continue
        if not tree or not staged or change["operation"] != "replace":
            raise ValueError("changes do not match Git base")
        mode, kind, blob = tree.split(b"\t", 1)[0].split()
        expected = mode + b" " + blob + b" 0\t" + name.encode() + b"\0"
        if kind != b"blob" or mode not in (b"100644", b"100755") or staged != expected:
            raise ValueError("source index differs from the reviewed base")
        content = git(root, "cat-file", "blob", blob.decode("ascii"))
        if hashlib.sha256(content).hexdigest() != change["before_sha256"]:
            raise ValueError("working copy differs from the reviewed commit")


def publish(root, base, edits, changes, digest, verify_sources):
    if base_commit(root) != base:
        raise ValueError("Git base changed")
    check_base(root, base, changes)
    with tempfile.TemporaryDirectory(prefix="cli-open-index-") as directory:
        index = Path(directory) / "index"
        git(root, "read-tree", base, index=index)
        for edit in edits:
            mode = "100644"
            if edit["operation"] == "replace":
                mode = git(root, "ls-tree", base, "--", edit["path"]).split()[0].decode("ascii")
            blob = git(root, "hash-object", "-w", "--stdin", data=edit["text"].encode("utf-8")).strip()
            git(root, "update-index", "--add", "--cacheinfo",
                f"{mode},{blob.decode('ascii')},{edit['path']}", index=index)
        tree = git(root, "write-tree", index=index).decode("ascii").strip()
        commit = git(root, "commit-tree", tree, "-p", base, "-m",
                     "Reviewed CLI_OPEN workspace changes").decode("ascii").strip()
    if not OID.fullmatch(commit):
        raise ValueError("invalid Git commit")
    check_base(root, base, changes)
    verify_sources(root, changes)
    reference = f"refs/heads/cli-open/review-{digest}"
    transaction = f"start\nverify HEAD {base}\ncreate {reference} {commit}\nprepare\ncommit\n"
    git(root, "update-ref", "--stdin", data=transaction.encode("ascii"))
    return reference, commit
