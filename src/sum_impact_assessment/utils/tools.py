import json
from ..schemas import LivingLab, Measure

def load_living_labs_from_file(file_path: str) -> list[LivingLab]:
    """
    Load a list of LivingLab instances from a given JSON file path.
    """
    with open(file_path, "r") as f:
        data = json.load(f)
    return [LivingLab(**lab) for lab in data]

def load_measures_from_file(file_path: str) -> list[Measure]:
    """
    Load a list of Measures instances from a given JSON file path.
    """
    with open(file_path, "r") as f:
        data = json.load(f)
    return [Measure(**m) for m in data]