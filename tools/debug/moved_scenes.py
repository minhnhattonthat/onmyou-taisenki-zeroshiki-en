"""After a rebuild that moves built text addresses: which coverage scenes to re-run.

    python -X utf8 tools/debug/moved_scenes.py OLD_strings.tsv [--new build/strings.tsv]

Compares the old and new id -> address maps, finds the logs under work/qa/cover that read each moved id's OLD
address (those runs showed it on the old build), and prints a small set of scene dirs (greedy cover, relative to
work/qa/cover) whose re-run on the new build shows every moved id again. Also prints moved ids no log ever showed.
"""
import argparse
import collections
import glob
import os
import re


def load(path):
    return dict(l.split("\t") for l in open(path, encoding="utf-8").read().split("\n") if l)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("old")
    ap.add_argument("--new", default="build/strings.tsv")
    a = ap.parse_args()
    old, new = load(a.old), load(a.new)
    moved = [k for k in new if k in old and old[k] != new[k]]
    inv = {v: k for k, v in new.items()}
    clash = [(k, inv[old[k]]) for k in moved if old[k] in inv]
    print(f"{len(moved)} moved ids; old address = another id's new address: {clash or 'none'}")
    need = {old[k].lstrip("0"): k for k in moved}
    hits = collections.defaultdict(set)
    for f in glob.glob("work/qa/cover/**/log.txt", recursive=True):
        rel = os.path.relpath(os.path.dirname(f), "work/qa/cover").replace(os.sep, "/")
        for m in re.finditer(r"TEXT ([0-9A-F]+)", open(f, encoding="utf-8", errors="replace").read()):
            if m.group(1) in need:
                hits[m.group(1)].add(rel)
    by_scene = collections.defaultdict(set)
    for addr, scenes in hits.items():
        for s in scenes:
            by_scene[s].add(addr)
    left, pick = set(hits), []
    while left:
        s = max(by_scene, key=lambda s: (len(by_scene[s] & left), -len(s)))
        pick.append(s)
        left -= by_scene[s]
    print("never shown before:", sorted(need[x] for x in need if x not in hits))
    print(" ".join(pick))


if __name__ == "__main__":
    main()
