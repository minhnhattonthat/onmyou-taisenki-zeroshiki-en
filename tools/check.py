"""check.py: the repo's one-command check (tests + text lint). The pre-commit hook runs it; exit code gates commits."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

steps = [[sys.executable, "-X", "utf8", "-m", "pytest", "-q", str(ROOT / "tests")]]
lint = ROOT / "tools" / "lint.py"
if lint.exists():
    steps.append([sys.executable, "-X", "utf8", str(lint)])
batches = ROOT / "tools" / "batches.py"
if batches.exists():  # glossary terms and Avoid spellings in all shipped English
    steps.append([sys.executable, "-X", "utf8", str(batches), "check"])

for cmd in steps:
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode:
        sys.exit(r.returncode)
print("check ok")
