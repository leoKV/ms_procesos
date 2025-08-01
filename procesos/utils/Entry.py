from dataclasses import dataclass

@dataclass
class Entry:
    type:int
    filename: str
    length1: int
    length2: int
    offset: int
    flags: int