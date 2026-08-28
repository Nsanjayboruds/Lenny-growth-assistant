"""
ingestion/download.py — Clone or update the Lenny's Podcast transcript repository.
"""
from __future__ import annotations

import os
import subprocess
import sys

REPO_URL = "https://github.com/ChatPRD/lennys-podcast-transcripts.git"
CLONE_DIR = os.path.join(os.path.dirname(__file__), "lennys-podcast-transcripts")


def download_transcripts(force_update: bool = False) -> str:
    """
    Clone the transcript repository if it doesn't exist, or pull updates.

    Returns:
        Path to the cloned repository directory.
    """
    if os.path.isdir(CLONE_DIR):
        if force_update:
            print(f"[download] Pulling latest from {REPO_URL}...")
            result = subprocess.run(
                ["git", "pull"],
                cwd=CLONE_DIR,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print(f"[download] git pull failed: {result.stderr}", file=sys.stderr)
            else:
                print(f"[download] Updated: {result.stdout.strip()}")
        else:
            print(f"[download] Transcript repo already exists at {CLONE_DIR}. Skipping clone.")
    else:
        print(f"[download] Cloning {REPO_URL} → {CLONE_DIR} ...")
        result = subprocess.run(
            ["git", "clone", "--depth=1", REPO_URL, CLONE_DIR],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"[download] git clone failed:\n{result.stderr}", file=sys.stderr)
            sys.exit(1)
        print(f"[download] Cloned successfully.")

    return CLONE_DIR


if __name__ == "__main__":
    path = download_transcripts(force_update="--update" in sys.argv)
    print(f"Transcripts available at: {path}")
