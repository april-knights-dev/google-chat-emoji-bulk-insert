#!/usr/bin/env python3
"""
Google Chat Emoji Bulk Uploader

Upload Slack-exported emojis to Google Chat in bulk.
Validates images and names, skips invalid ones, and uploads all valid emojis.
"""

import argparse
import sys
import time
from pathlib import Path

from src.auth import get_credentials
from src.validator import validate_emoji, ValidationResult
from src.emoji_uploader import EmojiUploader, UploadResult


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

    extensions = ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.PNG', '*.JPG', '*.JPEG', '*.GIF']
    files = []
    for ext in extensions:
        files.extend(path.glob(ext))

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
    """Print validation summary."""
    total = len(valid) + len(invalid)

    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Total files: {total}")
    print(f"Valid:       {len(valid)}")
    print(f"Invalid:     {len(invalid)}")

    if invalid:
        print("\n--- SKIPPED (Invalid) ---")
        for result in invalid:
            print(f"  {result}")

    print("=" * 60 + "\n")


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
        print("\n--- FAILED UPLOADS ---")
        for result in failed:
            print(f"  {result}")

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

    # Exit with error code if any uploads failed
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
