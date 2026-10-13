from abc import ABC, abstractmethod

class BaseBot(ABC):
    """
    Interface cơ bản cho Bot. 
    Các sinh viên có thể kế thừa (hoặc tự viết class Bot độc lập miễn là có hàm get_move).
    """
    @abstractmethod
    def get_move(self, state_dict: dict) -> dict:
        """
        Input: state_dict (dữ liệu board dạng JSON/dict)
        Output: dict có dạng {"from": [r, c], "to": [nr, nc]}
        """
        pass
