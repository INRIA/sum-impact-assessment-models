"""
Data loader utilities for loading static JSON configuration files.
"""
import json
from pathlib import Path
from typing import Dict, Any

# Path to data directory (relative to this file)
DATA_DIR = Path(__file__).parent.parent / "data"


def load_json_data(filename: str) -> Dict[str, Any]:
    """
    Load JSON data from the data directory.

    Args:
        filename: Name of the JSON file to load

    Returns:
        Parsed JSON data as dictionary

    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file is not valid JSON
    """
    file_path = DATA_DIR / filename
    with open(file_path, 'r') as f:
        return json.load(f)


def load_mcda_goal_weights() -> Dict[str, Dict[str, float]]:
    """
    Load MCDA goal weights configuration for different perspectives.

    Returns:
        Dictionary mapping perspective names to goal weights.
        Structure: {"perspective_name": {"Goal Name": weight, ...}, ...}

    Example:
        {
            "regulatory": {"Improve Safety": 0.4, "Improve Public Transport": 0.3},
            "pto": {"Improve Safety": 0.3, "Improve Public Transport": 0.4}
        }
    """
    return load_json_data("mcda_goal_weights.json")


def get_goal_weights_for_perspective(perspective: str) -> Dict[str, float]:
    """
    Get goal weights for a specific perspective.

    Args:
        perspective: The perspective name (e.g., "regulatory", "pto")

    Returns:
        Dictionary mapping goal names to their weights

    Raises:
        ValueError: If the perspective is not found in the configuration
    """
    all_weights = load_mcda_goal_weights()

    if perspective not in all_weights:
        available = ", ".join(all_weights.keys())
        raise ValueError(
            f"Perspective '{perspective}' not found in MCDA goal weights. "
            f"Available perspectives: {available}"
        )

    return all_weights[perspective]
