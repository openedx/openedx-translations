#!/usr/bin/env python3
"""
Update release branch translations with fixes and new strings from the main branch.

This script synchronizes translation files between a release branch and an upstream branch
(typically 'main'). It supports both JSON and PO (gettext) translation files.

Key features:
- Fetches upstream translations from a git branch (no local clone needed)
- Merges translations preferring upstream fixes over local versions
- Adds new translation strings from upstream that don't exist locally
- Preserves PO file formatting using msgcat with --no-wrap
- Supports filtering by language code and file type

For JSON files:
- Parses both local and upstream JSON files
- Adds new translation keys from upstream
- Preserves existing local translations for unchanged keys
- Sorts keys alphabetically for consistency

For PO files:
- Uses msgcat with --use-first to prefer upstream msgstr values (fixes)
- Uses --no-wrap to preserve original line formatting
- Uses --sort-output for consistent entry ordering
- Maintains proper gettext format and metadata

Usage:
    python update_from_main.py [OPTIONS]

Examples:
    # Update all languages and file types from main branch
    python update_from_main.py --branch main
    
    # Update only Portuguese translations
    python update_from_main.py --language pt_PT
    
    # Update only PO files for multiple languages
    python update_from_main.py --language pt_PT --language es_419 --file-type po
    
    # Dry run to preview changes
    python update_from_main.py --dry-run
    
    # Update from a different upstream repository
    python update_from_main.py --branch nau/redwood.master --upstream-repo https://github.com/openedx/openedx-translations.git
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional


def parse_args() -> argparse.Namespace:
    """
    Parse and validate command line arguments.
    
    Returns:
        Namespace object containing parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Update translations from upstream branch",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--branch",
        default="main",
        help="Upstream branch name to fetch translations from (default: main)"
    )
    parser.add_argument(
        "--upstream-repo",
        default="https://github.com/openedx/openedx-translations.git",
        help="Upstream repository URL (default: https://github.com/openedx/openedx-translations.git)"
    )
    parser.add_argument(
        "--language",
        "--languages",
        action="append",
        dest="languages",
        help="Language code(s) to process (e.g., pt_PT, es_419, fr_CA). "
             "Can be specified multiple times for batch processing. "
             "If omitted, all translation files will be processed."
    )
    parser.add_argument(
        "--file-type",
        choices=["json", "po", "both"],
        default="both",
        help="Type of translation files to process: 'json' for JSON files only, "
             "'po' for gettext PO files only, or 'both' for all files (default: both)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying any files. "
             "Shows which files would be updated and what changes would be made."
    )
    return parser.parse_args()


def run_command(cmd: list[str], cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
    """
    Run a shell command and return the result.
    
    Args:
        cmd: Command and arguments as a list
        cwd: Working directory for the command
        check: Whether to raise exception on non-zero exit code
    
    Returns:
        CompletedProcess instance with stdout, stderr, and returncode
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {' '.join(cmd)}", file=sys.stderr)
        print(f"Exit code: {e.returncode}", file=sys.stderr)
        print(f"stderr: {e.stderr}", file=sys.stderr)
        raise


def fetch_upstream_file(
    repo_path: Path,
    branch: str,
    file_path: str
) -> Optional[str]:
    """
    Fetch a file from the upstream git branch without checking it out.
    
    Uses 'git show' to read file content directly from the git object store,
    avoiding the need to checkout the branch or modify the working directory.
    
    Args:
        repo_path: Path to the cloned upstream repository
        branch: Branch name to fetch from (e.g., 'main', 'origin/redwood')
        file_path: Relative path to the file in the repository
    
    Returns:
        File content as string, or None if file doesn't exist in upstream branch
    """
    try:
        result = run_command(
            ["git", "show", f"{branch}:{file_path}"],
            cwd=repo_path
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return None


def merge_translations(
    current: Dict[str, Any],
    upstream: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Merge upstream translations into current translations for JSON files.
    
    Strategy:
    - Preserves all existing keys and values from the current (local) file
    - Adds only NEW keys from upstream that don't exist in current
    - Does NOT override existing translations (use this for additive merging)
    - Sorts all keys alphabetically for consistency
    
    This is useful when you want to add new strings from upstream while
    keeping your local translations unchanged.
    
    Args:
        current: Current translation dictionary from local file
        upstream: Upstream translation dictionary from main branch
    
    Returns:
        Merged dictionary with sorted keys
    """
    merged = current.copy()
    
    for key, value in upstream.items():
        if key not in merged:
            merged[key] = value
    
    # Sort keys alphabetically
    return dict(sorted(merged.items()))


def clone_upstream_repo(repo_url: str, branch: str, temp_dir: Path) -> Path:
    """
    Clone the upstream repository to a temporary directory using shallow clone.
    
    Uses git clone with --depth 1 for efficiency, fetching only the specified
    branch without full history. This significantly speeds up the operation
    and reduces disk space usage.
    
    Args:
        repo_url: Git repository URL (https or ssh)
        branch: Branch to checkout (e.g., 'main', 'nau/redwood.master')
        temp_dir: Temporary directory path where repo will be cloned
    
    Returns:
        Path to the cloned repository directory
    
    Raises:
        subprocess.CalledProcessError: If git clone fails
    """
    repo_path = temp_dir / "upstream-repo"
    
    print(f"Cloning upstream repository from {repo_url} (branch: {branch})...")
    
    # Clone with specific branch, shallow clone for efficiency
    run_command([
        "git", "clone",
        "--branch", branch,
        "--depth", "1",
        repo_url,
        str(repo_path)
    ])
    
    print(f"Repository cloned to {repo_path}")
    return repo_path


def find_translation_files(
    root_dir: Path,
    language_codes: Optional[list[str]] = None,
    file_type: str = "both"
) -> list[Path]:
    """
    Recursively find all translation files matching the criteria.
    
    File patterns:
    - JSON files: */{language_code}.json (e.g., src/i18n/messages/pt_PT.json)
    - PO files: */locale/{language_code}/LC_MESSAGES/*.po (standard gettext structure)
    
    Args:
        root_dir: Root directory to search from (typically translations/)
        language_codes: List of language codes (e.g., ['pt_PT', 'es_419']).
                       If None or empty, finds all translation files.
        file_type: Type of files to find:
                  - "json": Only JSON translation files
                  - "po": Only gettext PO files
                  - "both": All translation files (default)
    
    Returns:
        Sorted list of Path objects for matching files
    """
    files = set()
    
    if language_codes is None or len(language_codes) == 0:
        # Find all translation files if no language code specified
        if file_type in ("json", "both"):
            files.update(root_dir.rglob("*.json"))
        if file_type in ("po", "both"):
            files.update(root_dir.rglob("*.po"))
    else:
        # Find files matching any of the specified language codes
        for lang_code in language_codes:
            if file_type in ("json", "both"):
                pattern = f"{lang_code}.json"
                files.update(root_dir.rglob(pattern))
            if file_type in ("po", "both"):
                # PO files are in locale/{lang_code}/LC_MESSAGES/*.po
                files.update(root_dir.rglob(f"locale/{lang_code}/LC_MESSAGES/*.po"))
    
    return sorted(files)


def process_json_file(
    local_file: Path,
    upstream_repo: Path,
    branch: str,
    root_dir: Path,
    dry_run: bool = False
) -> bool:
    """
    Process a single JSON translation file by merging with upstream.
    
    Workflow:
    1. Read and parse the local JSON file
    2. Fetch and parse the corresponding upstream JSON file
    3. Merge translations (adds new keys from upstream)
    4. Compare merged result with current content
    5. Write back if changes detected (unless dry_run)
    
    Args:
        local_file: Path to local translation file
        upstream_repo: Path to cloned upstream repository
        branch: Branch name in upstream repo
        root_dir: Root directory of the project (for relative path calculation)
        dry_run: If True, show what would change but don't write files
    
    Returns:
        True if file was updated (or would be updated in dry_run), False otherwise
    """
    # Calculate relative path from root
    relative_path = local_file.relative_to(root_dir)
    
    # Read current local file
    try:
        with open(local_file, 'r', encoding='utf-8') as f:
            current_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse {relative_path}: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error: Failed to read {relative_path}: {e}", file=sys.stderr)
        return False
    
    # Fetch upstream file
    upstream_content = fetch_upstream_file(upstream_repo, branch, str(relative_path))
    
    if upstream_content is None:
        print(f"Warning: Missing upstream file for: {relative_path}", file=sys.stderr)
        return False
    
    try:
        upstream_data = json.loads(upstream_content)
    except json.JSONDecodeError as e:
        print(f"Warning: Failed to parse upstream JSON from {relative_path}: {e}", file=sys.stderr)
        return False
    
    # Merge translations
    merged_data = merge_translations(current_data, upstream_data)
    
    # Check if there are changes
    if merged_data == current_data:
        return False
    
    new_keys = set(merged_data.keys()) - set(current_data.keys())
    print(f"Updating {relative_path} (adding {len(new_keys)} new keys)")
    
    if dry_run:
        print(f"  [DRY RUN] Would update {local_file}")
        if new_keys:
            print(f"  New keys: {', '.join(sorted(list(new_keys)[:5]))}")
            if len(new_keys) > 5:
                print(f"  ... and {len(new_keys) - 5} more")
        return True
    
    # Write merged data back to file
    try:
        with open(local_file, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, ensure_ascii=False, indent=2)
            f.write('\n')  # Add trailing newline
        return True
    except Exception as e:
        print(f"Error: Failed to write {relative_path}: {e}", file=sys.stderr)
        return False


def process_po_file(
    local_file: Path,
    upstream_repo: Path,
    branch: str,
    root_dir: Path,
    dry_run: bool = False
) -> bool:
    """
    Process a single PO translation file by merging with upstream using msgcat.
    
    Workflow:
    1. Fetch upstream PO file content
    2. Write upstream content to temporary file
    3. Use msgcat to merge upstream and local files
    4. Compare merged result with current content
    5. Write back if changes detected (unless dry_run)
    
    msgcat options used:
    --use-first: When duplicate msgid found, use translation from first file (upstream)
                 This ensures upstream fixes take precedence over local versions
    --no-wrap: Prevent line wrapping, preserves original formatting of multi-line strings
    --sort-output: Sort entries by msgid for consistent file organization
    
    Args:
        local_file: Path to local PO translation file
        upstream_repo: Path to cloned upstream repository
        branch: Branch name in upstream repo
        root_dir: Root directory of the project (for relative path calculation)
        dry_run: If True, show what would change but don't write files
    
    Returns:
        True if file was updated (or would be updated in dry_run), False otherwise
    """
    # Calculate relative path from root
    relative_path = local_file.relative_to(root_dir)
    
    # Fetch upstream file
    upstream_content = fetch_upstream_file(upstream_repo, branch, str(relative_path))
    
    if upstream_content is None:
        print(f"Warning: Missing upstream file for: {relative_path}", file=sys.stderr)
        return False
    
    # Create temporary file for upstream content
    with tempfile.NamedTemporaryFile(mode='w', suffix='.po', delete=False, encoding='utf-8') as temp_upstream:
        temp_upstream.write(upstream_content)
        temp_upstream_path = temp_upstream.name
    
    try:
        # Use msgcat to merge PO files with formatting preservation
        # --use-first: use translations from first file when there are duplicates
        # --no-wrap: do not break long lines (preserves original formatting)
        # --sort-output: sort entries by msgid for consistency
        # Upstream file is first, so its translations (fixes) take precedence
        result = run_command(
            ["msgcat", "--use-first", "--no-wrap", "--sort-output", 
             temp_upstream_path, str(local_file)],
            check=False
        )
        
        if result.returncode != 0:
            print(f"Error: msgcat failed for {relative_path}: {result.stderr}", file=sys.stderr)
            return False
        
        merged_content = result.stdout
        
        # Read current local file to compare
        with open(local_file, 'r', encoding='utf-8') as f:
            current_content = f.read()
        
        # Check if there are changes
        if merged_content == current_content:
            return False
        
        print(f"Updating {relative_path}")
        
        if dry_run:
            print(f"  [DRY RUN] Would update {local_file}")
            return True
        
        # Write merged content back to file
        with open(local_file, 'w', encoding='utf-8') as f:
            f.write(merged_content)
        
        return True
        
    finally:
        # Clean up temporary file
        Path(temp_upstream_path).unlink(missing_ok=True)


def process_translation_file(
    local_file: Path,
    upstream_repo: Path,
    branch: str,
    root_dir: Path,
    dry_run: bool = False
) -> bool:
    """
    Process a single translation file by merging with upstream.
    
    Dispatcher function that routes to the appropriate handler based on
    file extension (.json or .po). Each file type has its own merge strategy.
    
    Args:
        local_file: Path to local translation file
        upstream_repo: Path to cloned upstream repository
        branch: Branch name in upstream repo
        root_dir: Root directory of the project
        dry_run: If True, preview changes without writing
    
    Returns:
        True if file was updated (or would be in dry_run), False otherwise
    """
    if local_file.suffix == '.json':
        return process_json_file(local_file, upstream_repo, branch, root_dir, dry_run)
    elif local_file.suffix == '.po':
        return process_po_file(local_file, upstream_repo, branch, root_dir, dry_run)
    else:
        print(f"Warning: Unsupported file type: {local_file}", file=sys.stderr)
        return False


def main():
    """
    Main entry point for the translation update script.
    
    Workflow:
    1. Parse command line arguments
    2. Validate workspace structure (translations/ directory exists)
    3. Find all translation files matching criteria
    4. Clone upstream repository to temporary directory
    5. Process each translation file (merge with upstream)
    6. Report summary of changes
    7. Clean up temporary files
    
    Exit codes:
    0: Success
    1: Error (missing directory, clone failed, etc.)
    """
    args = parse_args()
    
    # Determine workspace structure
    # Script expects to be run from repository root with translations/ subdirectory
    root_dir = Path.cwd()
    translations_dir = root_dir / "translations"
    
    if not translations_dir.exists():
        print("Error: 'translations' directory not found in current directory", file=sys.stderr)
        print(f"Current directory: {root_dir}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Processing translations in: {translations_dir}")
    print(f"Upstream branch: {args.branch}")
    print(f"Upstream repo: {args.upstream_repo}")
    print(f"File type: {args.file_type}")
    
    if args.languages:
        print(f"Languages: {', '.join(args.languages)}")
    else:
        print("Languages: all")
    
    if args.dry_run:
        print("\n*** DRY RUN MODE - No changes will be made ***\n")
    
    # Find all translation files
    translation_files = find_translation_files(translations_dir, args.languages, args.file_type)
    
    if not translation_files:
        lang_desc = ', '.join(args.languages) if args.languages else 'all'
        print(f"No {args.file_type} translation files for languages '{lang_desc}' found in {translations_dir}")
        sys.exit(0)
    
    print(f"Found {len(translation_files)} translation file(s)\n")
    
    # Use temporary directory for upstream clone (automatically cleaned up)
    # This avoids polluting the workspace and ensures clean state on each run
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        try:
            upstream_repo = clone_upstream_repo(args.upstream_repo, args.branch, temp_path)
        except subprocess.CalledProcessError:
            print(f"Error: Failed to clone upstream repository", file=sys.stderr)
            sys.exit(1)
        
        print()
        
        # Process each translation file individually
        # Track how many files were actually updated
        updated_count = 0
        for translation_file in translation_files:
            if process_translation_file(
                translation_file,
                upstream_repo,
                args.branch,
                root_dir,
                dry_run=args.dry_run
            ):
                updated_count += 1
        
        print(f"\n{'Would update' if args.dry_run else 'Updated'} {updated_count} of {len(translation_files)} file(s)")
    
    if args.dry_run:
        print("\nRun without --dry-run to apply changes")


if __name__ == "__main__":
    main()
