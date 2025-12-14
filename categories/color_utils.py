"""
Color utility functions for category color management.

This module provides deterministic color calculation for hierarchical categories:
- Root categories get distinct, high-contrast colors
- Child categories derive colors from their parent
- Siblings get progressively lighter colors based on ascending ID order
"""
import colorsys
from typing import List, Tuple


# Predefined high-contrast colors for root categories
# These colors are chosen to be visually distinct with good contrast
ROOT_COLORS = [
    '#FF6B6B',  # Red
    '#4ECDC4',  # Teal
    '#9B59B6',  # Purple
    '#96CEB4',  # Mint
    '#FFEAA7',  # Yellow
    '#F7DC6F',  # Gold
    '#45B7D1',  # Blue
    '#DDA0DD',  # Plum
    '#98D8C8',  # Seafoam
    '#3498DB',  # Sky Blue
    '#E67E22',  # Orange
    '#F39C12',  # Amber
    '#E91E63',  # Pink
    '#00BCD4',  # Cyan
    '#607D8B',  # Blue Grey
    '#16a34a',  # Green
    '#95A5A6',  # Grey
    '#2ECC71',  # Emerald
    '#E74C3C',  # Dark Red
    '#8E44AD',  # Dark Purple
]


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """
    Convert hex color string to RGB tuple.
    
    Args:
        hex_color: Hex color string (e.g., '#FF6B6B' or 'FF6B6B')
    
    Returns:
        Tuple of (R, G, B) values in range 0-255
    """
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        raise ValueError(f"Invalid hex color: {hex_color}")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb: Tuple[float, float, float]) -> str:
    """
    Convert RGB tuple to hex color string.
    
    Args:
        rgb: Tuple of (R, G, B) values (0-255 range)
    
    Returns:
        Hex color string (e.g., '#FF6B6B')
    """
    r, g, b = rgb
    return '#{:02X}{:02X}{:02X}'.format(
        int(max(0, min(255, r))),
        int(max(0, min(255, g))),
        int(max(0, min(255, b)))
    )


def hex_to_hsl(hex_color: str) -> Tuple[float, float, float]:
    """
    Convert hex color to HSL tuple.
    
    Args:
        hex_color: Hex color string (e.g., '#FF6B6B')
    
    Returns:
        Tuple of (H, S, L) values:
        - H: Hue in range 0.0-1.0
        - S: Saturation in range 0.0-1.0
        - L: Lightness in range 0.0-1.0
    """
    rgb = hex_to_rgb(hex_color)
    r, g, b = [x / 255.0 for x in rgb]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return (h, s, l)


def hsl_to_hex(hsl: Tuple[float, float, float]) -> str:
    """
    Convert HSL tuple to hex color string.
    
    Args:
        hsl: Tuple of (H, S, L) values (all in range 0.0-1.0)
    
    Returns:
        Hex color string (e.g., '#FF6B6B')
    """
    h, s, l = hsl
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return rgb_to_hex((r * 255, g * 255, b * 255))


def lighten_color(hex_color: str, lightness_increase: float) -> str:
    """
    Lighten a color by increasing its lightness while preserving hue and saturation.
    
    Args:
        hex_color: Base hex color string
        lightness_increase: Amount to increase lightness (0.0-1.0)
    
    Returns:
        Lightened hex color string
    """
    h, s, l = hex_to_hsl(hex_color)
    # Increase lightness, but cap at 0.95 to avoid pure white
    new_l = min(0.95, l + lightness_increase)
    return hsl_to_hex((h, s, new_l))


def get_root_color(index: int) -> str:
    """
    Get a distinct color for a root category based on its index.
    
    Args:
        index: Zero-based index of the root category (typically based on ID or creation order)
    
    Returns:
        Hex color string for the root category
    """
    # Cycle through predefined colors if we have more root categories than colors
    return ROOT_COLORS[index % len(ROOT_COLORS)]


def calculate_child_color(
    parent_color: str,
    sibling_id: int,
    sibling_ids: List[int],
    base_lightness_increase: float = 0.15
) -> str:
    """
    Calculate color for a child category based on parent color and sibling order.
    
    Children are lighter than their parent. Among siblings, colors get progressively
    lighter based on ascending ID order (lower ID = closer to parent, higher ID = lighter).
    
    Args:
        parent_color: Hex color of the parent category
        sibling_id: ID of the current child category
        sibling_ids: List of all sibling IDs (same parent), sorted ascending
        base_lightness_increase: Base amount to lighten from parent (default: 0.15)
    
    Returns:
        Hex color string for the child category
    """
    if not sibling_ids:
        # No siblings, use base lightening
        return lighten_color(parent_color, base_lightness_increase)
    
    # Find position of this sibling in the sorted list
    try:
        position = sibling_ids.index(sibling_id)
    except ValueError:
        # ID not in list, use base lightening
        return lighten_color(parent_color, base_lightness_increase)
    
    total_siblings = len(sibling_ids)
    
    if total_siblings == 1:
        # Only one child, use base lightening
        return lighten_color(parent_color, base_lightness_increase)
    
    # Calculate progressive lightening based on position
    # Lower ID (position 0) = closer to parent (less lightening)
    # Higher ID (last position) = lighter (more lightening)
    # Range: base_lightness_increase to base_lightness_increase + 0.15
    min_lightness = base_lightness_increase
    max_lightness = base_lightness_increase + 0.15
    
    # Linear interpolation based on position
    if total_siblings > 1:
        factor = position / (total_siblings - 1)
    else:
        factor = 0
    
    lightness_increase = min_lightness + (max_lightness - min_lightness) * factor
    
    return lighten_color(parent_color, lightness_increase)


def get_category_color(
    category_id: int,
    parent_color: str = None,
    sibling_ids: List[int] = None
) -> str:
    """
    Calculate the appropriate color for a category.
    
    For root categories (parent_color is None), returns a distinct color.
    For child categories, derives color from parent with progressive lightening
    based on sibling ID order.
    
    Args:
        category_id: ID of the category
        parent_color: Hex color of parent category (None for root categories)
        sibling_ids: List of all sibling IDs sorted ascending (None for root categories)
    
    Returns:
        Hex color string for the category
    """
    if parent_color is None:
        # Root category - use index-based color
        # For deterministic results, use category_id - 1 as index
        # This ensures same ID always gets same color
        return get_root_color(category_id - 1)
    else:
        # Child category - derive from parent
        if sibling_ids is None:
            sibling_ids = []
        return calculate_child_color(parent_color, category_id, sibling_ids)

