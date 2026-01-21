#!/usr/bin/env python3
"""
Google Chat Emoji Bulk Uploader

Upload Slack-exported emojis to Google Chat in bulk.
Validates images and names, skips invalid ones, and uploads all valid emojis.
"""

import argparse
import shutil
import sys
import time
from pathlib import Path

from src.auth import get_credentials
from src.validator import (
    validate_emoji, ValidationResult,
    ERROR_CATEGORY_NAME, ERROR_CATEGORY_FORMAT, ERROR_CATEGORY_SIZE,
    ERROR_CATEGORY_DIMENSION, ERROR_CATEGORY_NOT_SQUARE, ERROR_CATEGORY_OTHER
)
from src.emoji_uploader import EmojiUploader, UploadResult


# Error category descriptions for user-friendly output
ERROR_DESCRIPTIONS = {
    ERROR_CATEGORY_NAME: "Invalid emoji name (must be lowercase alphanumeric, hyphens, underscores only)",
    ERROR_CATEGORY_FORMAT: "Unsupported format (must be PNG, JPEG, or GIF)",
    ERROR_CATEGORY_SIZE: "File too large (must be 256KB or less)",
    ERROR_CATEGORY_DIMENSION: "Invalid dimensions (must be 64-500px)",
    ERROR_CATEGORY_NOT_SQUARE: "Not square (width and height must be equal)",
    ERROR_CATEGORY_OTHER: "Other error (file not found or corrupted)",
}

# Upload error categories
UPLOAD_ERROR_INVALID_PAYLOAD = "invalid_payload"
UPLOAD_ERROR_RESERVED_NAME = "reserved_name"
UPLOAD_ERROR_NAME_TOO_LONG = "name_too_long"
UPLOAD_ERROR_INVALID_NAME = "invalid_name_api"
UPLOAD_ERROR_OTHER = "other_api_error"

UPLOAD_ERROR_DESCRIPTIONS = {
    UPLOAD_ERROR_INVALID_PAYLOAD: "Invalid payload (GIF encoding issue)",
    UPLOAD_ERROR_RESERVED_NAME: "Reserved or blocked name",
    UPLOAD_ERROR_NAME_TOO_LONG: "Name too long",
    UPLOAD_ERROR_INVALID_NAME: "Invalid name (API rejected)",
    UPLOAD_ERROR_OTHER: "Other API error",
}


def find_emoji_files(directory: str) -> list[str]:
    """
    Find all image files in the given directory.

    Args:
        directory: Path to the directory containing emoji images

    Returns:
        List of file paths
    """
    path = Path(directory)
    if not path.exists():
        print(f"Error: Directory not found: {directory}")
        sys.exit(1)

    extensions = ['*.png', '*.jpg', '*.jpeg', '*.gif']
    files = set()
    for ext in extensions:
        files.update(path.glob(ext))

    return [str(f) for f in sorted(files)]


def validate_all(files: list[str]) -> tuple[list[ValidationResult], list[ValidationResult]]:
    """
    Validate all emoji files.

    Args:
        files: List of file paths to validate

    Returns:
        Tuple of (valid_results, invalid_results)
    """
    valid = []
    invalid = []

    for file_path in files:
        result = validate_emoji(file_path)
        if result.is_valid:
            valid.append(result)
        else:
            invalid.append(result)

    return valid, invalid


def print_validation_summary(valid: list[ValidationResult], invalid: list[ValidationResult]) -> None:
    """Print validation summary with categorized errors."""
    total = len(valid) + len(invalid)

    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Total files: {total}")
    print(f"Valid:       {len(valid)}")
    print(f"Invalid:     {len(invalid)}")

    if invalid:
        # Group by error category
        by_category: dict[str, list[ValidationResult]] = {}
        for result in invalid:
            for cat in result.error_categories:
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(result)

        print("\n--- ERROR BREAKDOWN ---")
        for cat, results in sorted(by_category.items()):
            desc = ERROR_DESCRIPTIONS.get(cat, cat)
            print(f"\n[{cat}] {desc}")
            print(f"  Count: {len(results)}")
            # Show first 5 examples
            for r in results[:5]:
                print(f"    - {r.emoji_name}: {', '.join(r.errors)}")
            if len(results) > 5:
                print(f"    ... and {len(results) - 5} more")

    print("\n" + "=" * 60 + "\n")


def organize_invalid_files(invalid: list[ValidationResult], output_dir: str) -> None:
    """
    Organize invalid emoji files into folders by error category.

    Args:
        invalid: List of invalid validation results
        output_dir: Base directory to create error folders
    """
    base_path = Path(output_dir)
    base_path.mkdir(exist_ok=True)

    # Create category folders and copy files
    copied_count = 0
    for result in invalid:
        # Use the first (primary) error category for folder placement
        if result.error_categories:
            category = result.error_categories[0]
        else:
            category = ERROR_CATEGORY_OTHER

        category_dir = base_path / category
        category_dir.mkdir(exist_ok=True)

        # Copy the file
        src = Path(result.file_path)
        dst = category_dir / src.name
        if not dst.exists():
            shutil.copy2(src, dst)
            copied_count += 1

    print(f"\nOrganized {copied_count} invalid files into: {base_path}")
    print("Folders created:")
    for folder in sorted(base_path.iterdir()):
        if folder.is_dir():
            count = len(list(folder.glob("*")))
            desc = ERROR_DESCRIPTIONS.get(folder.name, folder.name)
            print(f"  {folder.name}/ ({count} files) - {desc}")


def upload_all(
    uploader: EmojiUploader,
    valid_emojis: list[ValidationResult],
    skip_existing: bool = True,
    delay: float = 0.5
) -> tuple[list[UploadResult], list[UploadResult]]:
    """
    Upload all valid emojis.

    Args:
        uploader: EmojiUploader instance
        valid_emojis: List of validated emoji results
        skip_existing: Whether to skip already existing emojis
        delay: Delay between uploads (rate limiting)

    Returns:
        Tuple of (success_results, failed_results)
    """
    success = []
    failed = []

    # Get existing emojis if skip_existing is enabled
    existing = set()
    if skip_existing:
        print("Checking existing emojis...")
        existing = uploader.list_existing_emojis()
        print(f"Found {len(existing)} existing emojis")

    total = len(valid_emojis)
    for i, emoji in enumerate(valid_emojis, 1):
        # Skip if already exists
        if skip_existing and emoji.emoji_name in existing:
            print(f"[{i}/{total}] SKIP (exists): {emoji.emoji_name}")
            continue

        print(f"[{i}/{total}] Uploading: {emoji.emoji_name}...", end=" ")
        result = uploader.upload_emoji(emoji.file_path, emoji.emoji_name)

        if result.success:
            print("OK")
            success.append(result)
        else:
            print(f"FAILED: {result.error}")
            failed.append(result)

        # Rate limiting
        if i < total:
            time.sleep(delay)

    return success, failed


def categorize_upload_error(error: str) -> str:
    """Categorize upload error based on error message."""
    error_lower = error.lower()

    if "invalid payload" in error_lower or "payload" in error_lower:
        return UPLOAD_ERROR_INVALID_PAYLOAD
    elif "too long" in error_lower or "length" in error_lower:
        return UPLOAD_ERROR_NAME_TOO_LONG
    elif "reserved" in error_lower or "blocked" in error_lower:
        return UPLOAD_ERROR_RESERVED_NAME
    elif "malformed" in error_lower or "invalid" in error_lower and "name" in error_lower:
        return UPLOAD_ERROR_INVALID_NAME
    else:
        return UPLOAD_ERROR_OTHER


def organize_failed_uploads(failed: list[UploadResult], output_dir: str) -> None:
    """
    Organize failed upload files into folders by error category.

    Args:
        failed: List of failed upload results
        output_dir: Base directory to create error folders
    """
    base_path = Path(output_dir)
    base_path.mkdir(exist_ok=True)

    copied_count = 0
    for result in failed:
        category = categorize_upload_error(result.error or "")

        category_dir = base_path / category
        category_dir.mkdir(exist_ok=True)

        src = Path(result.file_path)
        dst = category_dir / src.name
        if not dst.exists():
            shutil.copy2(src, dst)
            copied_count += 1

    print(f"\nOrganized {copied_count} failed upload files into: {base_path}")
    print("Folders created:")
    for folder in sorted(base_path.iterdir()):
        if folder.is_dir():
            count = len(list(folder.glob("*")))
            desc = UPLOAD_ERROR_DESCRIPTIONS.get(folder.name, folder.name)
            print(f"  {folder.name}/ ({count} files) - {desc}")


def print_upload_summary(success: list[UploadResult], failed: list[UploadResult]) -> None:
    """Print upload summary."""
    total = len(success) + len(failed)

    print("\n" + "=" * 60)
    print("UPLOAD SUMMARY")
    print("=" * 60)
    print(f"Attempted: {total}")
    print(f"Success:   {len(success)}")
    print(f"Failed:    {len(failed)}")

    if failed:
        # Group by error category
        by_category: dict[str, list[UploadResult]] = {}
        for result in failed:
            cat = categorize_upload_error(result.error or "")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(result)

        print("\n--- FAILED UPLOADS BY CATEGORY ---")
        for cat, results in sorted(by_category.items()):
            desc = UPLOAD_ERROR_DESCRIPTIONS.get(cat, cat)
            print(f"\n[{cat}] {desc}")
            print(f"  Count: {len(results)}")
            for r in results[:5]:
                print(f"    - {r.emoji_name}: {r.error}")
            if len(results) > 5:
                print(f"    ... and {len(results) - 5} more")

    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Upload Slack emojis to Google Chat in bulk"
    )
    parser.add_argument(
        "emoji_dir",
        help="Directory containing emoji images"
    )
    parser.add_argument(
        "--credentials",
        default="credentials.json",
        help="Path to OAuth credentials file (default: credentials.json)"
    )
    parser.add_argument(
        "--token",
        default="token.pickle",
        help="Path to token file (default: token.pickle)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only validate, don't upload"
    )
    parser.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Don't skip existing emojis (will fail on duplicates)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between uploads in seconds (default: 0.5)"
    )
    parser.add_argument(
        "--organize-errors",
        metavar="DIR",
        help="Copy invalid/failed files to DIR, organized by error category"
    )

    args = parser.parse_args()

    # Find emoji files
    print(f"Scanning directory: {args.emoji_dir}")
    files = find_emoji_files(args.emoji_dir)
    print(f"Found {len(files)} image files")

    if not files:
        print("No image files found. Exiting.")
        sys.exit(0)

    # Validate all files
    print("\nValidating emojis...")
    valid, invalid = validate_all(files)
    print_validation_summary(valid, invalid)

    # Organize invalid files if requested
    if args.organize_errors and invalid:
        organize_invalid_files(invalid, args.organize_errors)

    if not valid:
        print("No valid emojis to upload. Exiting.")
        sys.exit(0)

    if args.dry_run:
        print("Dry run mode - no uploads performed.")
        print(f"\n{len(valid)} emojis would be uploaded:")
        for v in valid:
            print(f"  - {v.emoji_name}")
        sys.exit(0)

    # Authenticate
    print("Authenticating with Google...")
    try:
        creds = get_credentials(args.credentials, args.token)
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        sys.exit(1)

    # Upload
    uploader = EmojiUploader(creds)
    print(f"\nUploading {len(valid)} emojis...")

    success, failed = upload_all(
        uploader,
        valid,
        skip_existing=not args.no_skip_existing,
        delay=args.delay
    )

    print_upload_summary(success, failed)

    # Organize failed upload files if requested
    if args.organize_errors and failed:
        upload_errors_dir = Path(args.organize_errors) / "upload_errors"
        organize_failed_uploads(failed, str(upload_errors_dir))

    # Exit with error code if any uploads failed
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
