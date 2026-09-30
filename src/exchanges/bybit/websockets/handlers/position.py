from src.strategy.inventory import Inventory
from src.sharedstate import SharedState


class BybitPositionHandler:

    def __init__(self, sharedstate: SharedState) -> None:
        self.ss = sharedstate

    def sync(self, recv: dict) -> None:
        positions = recv["result"]["list"]

        for data in positions:
            self.process(data)

    def process(self, data: list) -> None:
        # Bybit private position WS:
        # data = [position1, position2, ...]
        #
        # Nhưng private_feed hiện tại đang truyền nguyên `data`
        # vào handler, nên xử lý cả 2 trường hợp.

        if isinstance(data, list):
            for position in data:
                self._process_position(position)
        else:
            self._process_position(data)

    def _process_position(self, data: dict) -> None:
        side = data.get("side", "")

        # Empty side = không có position
        if not side:
            return

        position_value = float(data.get("positionValue") or 0)
        leverage = float(data.get("leverage") or 0)

        if position_value == 0 or leverage == 0:
            return

        Inventory(self.ss).position_delta(
            side,
            position_value,
            leverage
        )
