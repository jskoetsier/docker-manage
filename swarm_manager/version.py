"""
Version management for Docker Swarm Manager
"""

import os
import subprocess
from pathlib import Path

from django.conf import settings

BASE_DIR = Path(__file__).resolve().parent.parent


def get_version():
    """Get application version from VERSION file"""
    try:
        version_file = BASE_DIR / "VERSION"
        if version_file.exists():
            return version_file.read_text().strip()
        return "Unknown"
    except Exception:
        return "Unknown"


def get_git_info():
    """Get git commit information"""
    try:
        # Get current commit hash
        commit_hash = (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=BASE_DIR,
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )

        # Get current branch
        branch = (
            subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=BASE_DIR,
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )

        # Get commit date
        commit_date = (
            subprocess.check_output(
                ["git", "log", "-1", "--format=%cd", "--date=short"],
                cwd=BASE_DIR,
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )

        return {
            "commit_hash": commit_hash,
            "branch": branch,
            "commit_date": commit_date,
        }
    except Exception:
        return None


def get_build_info():
    """Get build information"""
    import platform
    import sys

    import django

    git_info = get_git_info()

    build_info = {
        "version": get_version(),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "django_version": django.get_version(),
        "platform": platform.system(),
        "architecture": platform.machine(),
    }

    if git_info:
        build_info.update(git_info)

    return build_info


def get_version_display():
    """Get formatted version string for display"""
    version = get_version()
    git_info = get_git_info()

    if git_info and git_info.get("commit_hash"):
        return f"{version} ({git_info['commit_hash']})"

    return version
