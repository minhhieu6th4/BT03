class Move:
    def __init__(self, from_pos: tuple[int, int], to_pos: tuple[int, int]):
        self.from_pos = from_pos
        self.to_pos = to_pos

    def to_dict(self):
        return {
            "from": list(self.from_pos),
            "to": list(self.to_pos)
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(tuple(data["from"]), tuple(data["to"]))

    def __eq__(self, other):
        if not isinstance(other, Move):
            return False
        return self.from_pos == other.from_pos and self.to_pos == other.to_pos

    def __repr__(self):
        return f"Move(from={self.from_pos}, to={self.to_pos})"

