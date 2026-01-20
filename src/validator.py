"""Validation module for emoji images and names."""

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from PIL import Image


# Google Chat emoji constraints
MAX_FILE_SIZE = 256 * 1024  # 256KB
MIN_DIMENSION = 64
MAX_DIMENSION = 500
ALLOWED_FORMATS = {'PNG', 'JPEG', 'GIF'}
NAME_PATTERN = re.compile(r'^[a-z0-9_-]+$')


@dataclass
class ValidationResult:
    """Result of emoji validation."""
    is_valid: bool
    file_path: str
    emoji_name: str
    errors: list[str]

    def __str__(self) -> str:
        if self.is_valid:
            return f"[OK] {self.emoji_name}"
        return f"[NG] {self.emoji_name}: {', '.join(self.errors)}"


def validate_name(name: str) -> list[str]:
    """
    Validate emoji name against Google Chat naming rules.

    Rules:
    - Only lowercase letters, numbers, hyphens, underscores allowed

    Args:
        name: The emoji name to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    if not name:
        errors.append("Name is empty")
        return errors

    if not NAME_PATTERN.match(name):
        errors.append(f"Invalid name '{name}': only lowercase letters, numbers, hyphens, underscores allowed")

    return errors


def validate_image(file_path: str) -> list[str]:
    """
    Validate image file against Google Chat emoji constraints.

    Constraints:
    - File size: <= 256KB
    - Dimensions: 64px - 500px square
    - Format: PNG, JPEG, GIF

    Args:
        file_path: Path to the image file

    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    path = Path(file_path)

    if not path.exists():
        errors.append(f"File not found: {file_path}")
        return errors

    # Check file size
    file_size = path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        errors.append(f"File too large: {file_size / 1024:.1f}KB (max: 256KB)")

    # Check image properties
    try:
        with Image.open(file_path) as img:
            # Check format
            img_format = img.format
            if img_format not in ALLOWED_FORMATS:
                errors.append(f"Invalid format: {img_format} (allowed: PNG, JPEG, GIF)")

            # Check dimensions
            width, height = img.size
            if width != height:
                errors.append(f"Not square: {width}x{height}")

            if width < MIN_DIMENSION or width > MAX_DIMENSION:
                errors.append(f"Invalid dimension: {width}px (must be 64-500px)")

            if height < MIN_DIMENSION or height > MAX_DIMENSION:
                errors.append(f"Invalid dimension: {height}px (must be 64-500px)")

    except Exception as e:
        errors.append(f"Cannot read image: {str(e)}")

    return errors


def extract_emoji_name(file_path: str) -> str:
    """
    Extract emoji name from file path.

    Slack exports emojis with format: emoji_name.png
    This function extracts the name and normalizes it.

    Args:
        file_path: Path to the emoji file

    Returns:
        Normalized emoji name
    """
    name = Path(file_path).stem
    # Convert to lowercase and replace invalid characters
    name = name.lower()
    return name


def validate_emoji(file_path: str, custom_name: Optional[str] = None) -> ValidationResult:
    """
    Validate a single emoji file.

    Args:
        file_path: Path to the emoji image file
        custom_name: Optional custom name (uses filename if not provided)

    Returns:
        ValidationResult with validation status and any errors
    """
    emoji_name = custom_name if custom_name else extract_emoji_name(file_path)
    errors = []

    # Validate name
    errors.extend(validate_name(emoji_name))

    # Validate image
    errors.extend(validate_image(file_path))

    return ValidationResult(
        is_valid=len(errors) == 0,
        file_path=file_path,
        emoji_name=emoji_name,
        errors=errors
    )
