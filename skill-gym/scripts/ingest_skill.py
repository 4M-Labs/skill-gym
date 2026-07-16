"""
ingest_skill.py -- Ingest a GitHub skill repository into the skill-gym pipeline.

Clones (or updates) a skill repository, validates its SKILL.md manifest,
extracts the skill card metadata, and registers it in the local skill catalog.

Usage:
    python ingest_skill.py --repo https://github.com/user/repo --skill-id my-skill
    python ingest_skill.py --repo https://github.com/user/repo --branch feature/skill --output-dir ./skills
    python ingest_skill.py --catalog ./catalog.json --list
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class SkillManifest:
    """Parsed representation of a SKILL.md file."""

    skill_id: str
    name: str
    description: str
    version: str
    author_name: str
    author_url: str
    license: str
    tags: list[str] = field(default_factory=list)
    raw_content: str = ""

    def to_skill_card(self) -> dict[str, Any]:
        """Convert manifest to a skill card dict."""
        return {
            "skill_id": self.skill_id,
            "version": self.version,
            "name": self.name,
            "description": self.description,
            "author": {"name": self.author_name, "url": self.author_url},
            "license": self.license,
            "tags": self.tags,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }


@dataclass
class IngestionResult:
    """Result of a skill ingestion operation."""

    skill_id: str
    repository_url: str
    commit_sha: str
    branch: str
    local_path: Path
    manifest_found: bool
    skill_card: dict[str, Any] | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.manifest_found and not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "repository_url": self.repository_url,
            "commit_sha": self.commit_sha,
            "branch": self.branch,
            "local_path": str(self.local_path),
            "manifest_found": self.manifest_found,
            "success": self.success,
            "errors": self.errors,
        }


# ---------------------------------------------------------------------------
# Git operations
# ---------------------------------------------------------------------------

def clone_or_update_repo(
    repo_url: str,
    target_dir: Path,
    branch: str | None = None,
) -> tuple[str, str]:
    """
    Clone a repository or update it if it already exists.

    Returns:
        Tuple of (commit_sha, branch_name).
    """
    if (target_dir / ".git").exists():
        print(f"  Updating existing repo at {target_dir}")
        subprocess.run(
            ["git", "fetch", "--all"],
            cwd=str(target_dir),
            check=True,
            capture_output=True,
        )
        if branch:
            subprocess.run(
                ["git", "checkout", branch],
                cwd=str(target_dir),
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "pull", "origin", branch],
                cwd=str(target_dir),
                check=True,
                capture_output=True,
            )
    else:
        print(f"  Cloning {repo_url} -> {target_dir}")
        clone_cmd = ["git", "clone", "--depth=1"]
        if branch:
            clone_cmd.extend(["--branch", branch])
        clone_cmd.extend([repo_url, str(target_dir)])
        subprocess.run(clone_cmd, check=True, capture_output=True)

    # Get current commit SHA
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(target_dir),
        capture_output=True,
        text=True,
        check=True,
    )
    commit_sha = result.stdout.strip()

    # Get current branch
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=str(target_dir),
        capture_output=True,
        text=True,
        check=True,
    )
    current_branch = result.stdout.strip()

    return commit_sha, current_branch


def get_repo_commit_sha(repo_dir: Path) -> str:
    """Get the full commit SHA of a repository."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(repo_dir),
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Manifest parsing
# ---------------------------------------------------------------------------

def parse_skill_md(skill_md_path: Path) -> SkillManifest | None:
    """
    Parse a SKILL.md file into a SkillManifest.

    Expects a simple markdown format with key-value sections.
    Returns None if the file cannot be parsed.
    """
    if not skill_md_path.exists():
        return None

    content = skill_md_path.read_text(encoding="utf-8")

    # Extract key fields using regex
    def extract_field(pattern: str, default: str = "") -> str:
        match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)
        return match.group(1).strip() if match else default

    skill_id = extract_field(r"Skill ID:\s*`([^`]+)`")
    name = extract_field(r"^#\s+(.+)", "Unnamed Skill")
    description = extract_field(r"## Description\s*\n\s*\n(.+?)(?=\n##|\Z)", "", )
    version = extract_field(r"Version:\s*`([^`]+)`", "0.0.1")
    author_name = extract_field(r"Author:\s*`([^`]+)`", "Unknown")
    author_url = extract_field(r"Author URL:\s*`([^`]+)`", "")
    license_val = extract_field(r"License:\s*`([^`]+)`", "MIT")

    # Extract tags
    tags_match = re.search(
        r"Tags\s*\n\s*\n(.+?)(?=\n##|\Z)", content, re.MULTILINE
    )
    tags = []
    if tags_match:
        tags = [
            t.strip().strip("`")
            for t in tags_match.group(1).split(",")
        ]

    if not skill_id:
        return None

    return SkillManifest(
        skill_id=skill_id,
        name=name,
        description=description,
        version=version,
        author_name=author_name,
        author_url=author_url,
        license=license_val,
        tags=tags,
        raw_content=content,
    )


# ---------------------------------------------------------------------------
# Catalog management
# ---------------------------------------------------------------------------

def load_catalog(catalog_path: Path) -> dict[str, Any]:
    """Load the skill catalog from disk."""
    if catalog_path.exists():
        with open(catalog_path, encoding="utf-8") as f:
            return json.load(f)
    return {"skills": {}, "last_updated": None}


def save_catalog(catalog_path: Path, catalog: dict[str, Any]) -> None:
    """Save the skill catalog to disk."""
    catalog["last_updated"] = datetime.now(timezone.utc).isoformat()
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)


def register_skill(catalog_path: Path, result: IngestionResult) -> None:
    """Register an ingested skill in the catalog."""
    catalog = load_catalog(catalog_path)

    catalog["skills"][result.skill_id] = {
        "repository_url": result.repository_url,
        "commit_sha": result.commit_sha,
        "branch": result.branch,
        "local_path": str(result.local_path),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }

    save_catalog(catalog_path, catalog)
    print(f"  Registered {result.skill_id} in catalog at {catalog_path}")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def ingest_skill(
    repo_url: str,
    skill_id: str | None = None,
    branch: str | None = None,
    output_dir: Path = Path("./skills"),
    catalog_path: Path = Path("./catalog.json"),
) -> IngestionResult:
    """
    Ingest a skill from a GitHub repository.

    Args:
        repo_url: GitHub repository URL.
        skill_id: Override skill ID (extracted from SKILL.md if not provided).
        branch: Branch to ingest from.
        output_dir: Directory to clone skills into.
        catalog_path: Path to the skill catalog file.

    Returns:
        IngestionResult with ingestion details.
    """
    # Derive skill ID from repo URL if not provided
    if not skill_id:
        skill_id = repo_url.rstrip("/").split("/")[-1].replace(".git", "")

    skill_dir = output_dir / skill_id

    print(f"\nIngesting skill: {skill_id}")
    print(f"  Repository: {repo_url}")

    result = IngestionResult(
        skill_id=skill_id,
        repository_url=repo_url,
        commit_sha="",
        branch=branch or "main",
        local_path=skill_dir,
        manifest_found=False,
    )

    try:
        # Clone or update
        commit_sha, current_branch = clone_or_update_repo(
            repo_url, skill_dir, branch
        )
        result.commit_sha = commit_sha
        result.branch = current_branch
        print(f"  Commit: {commit_sha[:12]}")

        # Find and parse SKILL.md
        skill_md_candidates = [
            skill_dir / "SKILL.md",
            skill_dir / "skill.md",
            skill_dir / "skills" / "SKILL.md",
        ]

        manifest = None
        for candidate in skill_md_candidates:
            manifest = parse_skill_md(candidate)
            if manifest:
                print(f"  Found SKILL.md at {candidate.relative_to(skill_dir)}")
                break

        if manifest is None:
            result.errors.append("No valid SKILL.md found in repository")
            return result

        result.manifest_found = True

        # Override skill ID if one was provided
        if skill_id:
            manifest.skill_id = skill_id

        # Build skill card
        skill_card = manifest.to_skill_card()
        skill_card["source"] = {
            "repository": repo_url,
            "commit_sha": commit_sha,
            "skill_md_path": str(candidate.relative_to(skill_dir)) if manifest else None,
        }
        result.skill_card = skill_card

        # Save skill card
        card_path = skill_dir / "skillcard.json"
        with open(card_path, "w", encoding="utf-8") as f:
            json.dump(skill_card, f, indent=2)
        print(f"  Saved skill card to {card_path}")

        # Register in catalog
        register_skill(catalog_path, result)

    except subprocess.CalledProcessError as exc:
        result.errors.append(f"Git operation failed: {exc}")
    except Exception as exc:
        result.errors.append(f"Unexpected error: {type(exc).__name__}: {exc}")

    return result


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI entry point for skill ingestion."""
    parser = argparse.ArgumentParser(
        description="Ingest a GitHub skill repository into skill-gym.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python ingest_skill.py --repo https://github.com/user/skill-repo
              python ingest_skill.py --repo https://github.com/user/repo --skill-id my-skill
              python ingest_skill.py --catalog ./catalog.json --list
        """),
    )
    parser.add_argument(
        "--repo",
        type=str,
        help="GitHub repository URL to ingest.",
    )
    parser.add_argument(
        "--skill-id",
        type=str,
        default=None,
        help="Override skill ID (extracted from SKILL.md if not provided).",
    )
    parser.add_argument(
        "--branch",
        type=str,
        default=None,
        help="Branch to ingest from (default: repository default branch).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./skills"),
        help="Directory to clone skills into (default: ./skills).",
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("./catalog.json"),
        help="Path to skill catalog file (default: ./catalog.json).",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all skills in the catalog and exit.",
    )

    args = parser.parse_args()

    if args.list:
        catalog = load_catalog(args.catalog)
        if not catalog.get("skills"):
            print("No skills in catalog.")
        else:
            print(f"\n{'Skill ID':<30} {'Branch':<15} {'Commit':<12}")
            print("-" * 60)
            for sid, info in catalog["skills"].items():
                print(
                    f"{sid:<30} {info.get('branch', '?'):<15} "
                    f"{info.get('commit_sha', '?')[:12]:<12}"
                )
        sys.exit(0)

    if not args.repo:
        parser.error("--repo is required when not using --list")

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    result = ingest_skill(
        repo_url=args.repo,
        skill_id=args.skill_id,
        branch=args.branch,
        output_dir=output_dir,
        catalog_path=args.catalog,
    )

    if result.success:
        print(f"\nSuccessfully ingested {result.skill_id}")
        print(json.dumps(result.to_dict(), indent=2))
        sys.exit(0)
    else:
        print(f"\nIngestion failed for {result.skill_id}:")
        for err in result.errors:
            print(f"  - {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
