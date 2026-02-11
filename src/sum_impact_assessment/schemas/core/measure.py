from pydantic import BaseModel

class Measure(BaseModel):
    """
    Measure schema:
    - id: unique identifier
    - name: name of the push or pull measure
    - times_implemented: number of times measure is implemented in living lab. Always 0 or 1 for simple measures, and 0,...,N to a group of N measures.
    """
    id: str
    name: str
    times_implemented: int