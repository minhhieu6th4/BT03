class Move:
    def __init__(self, from_pos: tuple[int, int], to_pos: tuple[int, int]):
        self.from_pos = from_pos
        self.to_pos = to_pos

    def to_dict(self) -> dict:
        return {
            "from": list(self.from_pos),
            "to": list(self.to_pos)
        }
