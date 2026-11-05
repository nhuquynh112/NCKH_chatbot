"""Create a new result directory from locked inputs, then run without touching old results."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys

from controlled_study.run import verify_lock


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--new-root", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--gpu-python", type=Path, required=True)
    args = parser.parse_args()
    source, target = args.source.resolve(), args.new_root.resolve()
    lock = verify_lock(source)
    if target.exists():
        raise ValueError("New result directory already exists; refusing to overwrite")
    if target.is_relative_to(source):
        raise ValueError("New run must be outside the old evidence directory")
    target.mkdir(parents=True)
    for name in [*lock["input_sha256"], "lock.json"]:
        original = (source / name).resolve()
        destination = (target / name).resolve()
        if not original.is_relative_to(source) or not destination.is_relative_to(target):
            raise ValueError("Unsafe inventory path")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, destination)
    verify_lock(target)
    print("Replaying the same known test set, not creating a new unseen holdout. Old ratings do not automatically apply.", flush=True)
    result = subprocess.run([sys.executable, "-B", "-m", "controlled_study.run", "--root", str(target),
                             "--profile", str(args.profile.resolve()), "--gpu-python", str(args.gpu_python.resolve())])
    sys.exit(result.returncode)
