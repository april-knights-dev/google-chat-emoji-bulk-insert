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


# Error categories for folder organization
ERROR_CATEGORY_NAME = "invalid_name"
ERROR_CATEGORY_FORMAT = "invalid_format"
ERROR_CATEGORY_SIZE = "too_large"
ERROR_CATEGORY_DIMENSION = "invalid_dimension"
ERROR_CATEGORY_NOT_SQUARE = "not_square"
ERROR_CATEGORY_OTHER = "other_error"


@dataclass
class ValidationResult:
    """Result of emoji validation."""
    is_valid: bool
    file_path: str
    emoji_name: str
    errors: list[str]
    error_categories: list[str] = None

    def __post_init__(self):
        if self.error_categories is None:
            self.error_categories = []

    def __str__(self) -> str:
        if self.is_valid:
            return f"[OK] {self.emoji_name}"
        return f"[NG] {self.emoji_name}: {', '.join(self.errors)}"


def validate_name(name: str) -> tuple[list[str], list[str]]:
    """
    Validate emoji name against Google Chat naming rules.

    Rules:
    - Only lowercase letters, numbers, hyphens, underscores allowed

    Args:
        name: The emoji name to validate

    Returns:
        Tuple of (error messages, error categories)
    """
    errors = []
    categories = []

    if not name:
        errors.append("Name is empty")
        categories.append(ERROR_CATEGORY_NAME)
        return errors, categories

    if not NAME_PATTERN.match(name):
        errors.append(f"Invalid name '{name}': only lowercase letters, numbers, hyphens, underscores allowed")
        categories.append(ERROR_CATEGORY_NAME)

    return errors, categories


def validate_image(file_path: str) -> tuple[list[str], list[str]]:
    """
    Validate image file against Google Chat emoji constraints.

    Constraints:
    - File size: <= 256KB
    - Dimensions: 64px - 500px square
    - Format: PNG, JPEG, GIF

    Args:
        file_path: Path to the image file

    Returns:
        Tuple of (error messages, error categories)
    """
    errors = []
    categories = []
    path = Path(file_path)

    if not path.exists():
        errors.append(f"File not found: {file_path}")
        categories.append(ERROR_CATEGORY_OTHER)
        return errors, categories

    # Check file size
    file_size = path.stat().st_size
    if file_size > MAX_FILE_SIZE:
        errors.append(f"File too large: {file_size / 1024:.1f}KB (max: 256KB)")
        categories.append(ERROR_CATEGORY_SIZE)

    # Check image properties
    try:
        with Image.open(file_path) as img:
            # Check format
            img_format = img.format
            if img_format not in ALLOWED_FORMATS:
                errors.append(f"Invalid format: {img_format} (allowed: PNG, JPEG, GIF)")
                categories.append(ERROR_CATEGORY_FORMAT)

            # Check dimensions
            width, height = img.size
            if width != height:
                errors.append(f"Not square: {width}x{height}")
                categories.append(ERROR_CATEGORY_NOT_SQUARE)

            if width < MIN_DIMENSION or width > MAX_DIMENSION:
                errors.append(f"Invalid dimension: {width}px (must be 64-500px)")
                if ERROR_CATEGORY_DIMENSION not in categories:
                    categories.append(ERROR_CATEGORY_DIMENSION)

            if height < MIN_DIMENSION or height > MAX_DIMENSION:
                errors.append(f"Invalid dimension: {height}px (must be 64-500px)")
                if ERROR_CATEGORY_DIMENSION not in categories:
                    categories.append(ERROR_CATEGORY_DIMENSION)

    except Exception as e:
        errors.append(f"Cannot read image: {str(e)}")
        categories.append(ERROR_CATEGORY_OTHER)

    return errors, categories


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
    categories = []

    # Validate name
    name_errors, name_categories = validate_name(emoji_name)
    errors.extend(name_errors)
    categories.extend(name_categories)

    # Validate image
    image_errors, image_categories = validate_image(file_path)
    errors.extend(image_errors)
    categories.extend(image_categories)

    return ValidationResult(
        is_valid=len(errors) == 0,
        file_path=file_path,
        emoji_name=emoji_name,
        errors=errors,
        error_categories=categories
    )
