"""Check that a machine can run the Smart Hub: Python, pinned packages, theme file, data shares.

Run it on the server with the same Python that runs Streamlit, from any folder:

    python scripts/check_server.py

It only reads: versions, file existence and folder listings. Exit code 1 if anything is missing.
"""
import os
import sys
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIN_PYTHON = (3, 11)
OK, BAD, WARN = "OK  ", "FAIL", "WARN"
problems = 0


def report(status, what, detail=""):
    global problems
    problems += status == BAD
    print(f"  [{status}] {what}" + (f"  ({detail})" if detail else ""))


print(f"Smart Hub server check  -  {ROOT}\n")

print("Python")
v = sys.version_info
report(OK if v[:2] >= MIN_PYTHON else BAD, f"Python {v.major}.{v.minor}.{v.micro}",
       f"needs {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+, executable {sys.executable}")

print("\nPackages (requirements.txt)")
for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
    line = line.split("#")[0].strip()
    if not line:
        continue
    name, _, wanted = line.partition("==")
    try:
        have = metadata.version(name)
    except metadata.PackageNotFoundError:
        report(BAD, f"{name} not installed", f"install {line}")
        continue
    report(OK if have == wanted else WARN, f"{name} {have}", "" if have == wanted else f"pinned {wanted}")

print("\nApp files")
for rel in ("My_Streamlit_app.py", "config.py", "ui.py", ".streamlit/config.toml", "app_pages"):
    report(OK if (ROOT / rel).exists() else BAD, rel)
if (ROOT / "Pages").is_dir() or (ROOT / "pages").is_dir():
    report(WARN, "a Pages/ folder exists", "Streamlit auto-discovers it; the pages now live in app_pages/")

print("\nData shares (config.py, network mode)")
os.environ.pop("USE_SAMPLE_DATA", None)
sys.path.insert(0, str(ROOT))
import config  # noqa: E402

for key, path in config._NETWORK.items():
    p = Path(path)
    try:
        if p.suffix:  # a file
            report(OK if p.is_file() else BAD, key, path)
        else:
            n = len(os.listdir(p))
            report(OK if n else WARN, key, f"{path}  -  {n} files")
    except OSError as e:
        report(BAD, key, f"{path}  -  {e.strerror or e}")

print("\n" + ("All checks passed." if not problems else f"{problems} problem(s) found."))
print("Start the hub from this folder (so .streamlit/config.toml is read):")
print(f'  cd "{ROOT}"\n  "{sys.executable}" -m streamlit run My_Streamlit_app.py')
sys.exit(1 if problems else 0)
