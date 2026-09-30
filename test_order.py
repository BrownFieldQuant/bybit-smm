import asyncio
import math
import requests

from src.sharedstate import SharedState
from src.exchanges.bybit.post.order import Order


def get_bbo(symbol):
    url = "https://api.bybit.com/v5/market/tickers"

    response = requests.get(
        url,
        params={
            "category": "linear",
            "symbol": symbol,
        },
        timeout=10,
    )

    response.raise_for_status()
    data = response.json()

    if data["retCode"] != 0:
        raise RuntimeError(data["retMsg"])

    item = data["result"]["list"][0]

    return float(item["bid1Price"]), float(item["ask1Price"])


async def main():
    ss = SharedState()

    # Lấy BBO THẬT từ Bybit REST
    bid, ask = get_bbo(ss.bybit_symbol)

    print(f"Symbol : {ss.bybit_symbol}")
    print(f"Bid    : {bid}")
    print(f"Ask    : {ask}")

    # Buy thấp hơn best bid 1 tick -> PostOnly
    price = bid - ss.bybit_tick_size

    # Bybit minimum notional = 5 USDT.
    # Dùng 5.10 USDT để có một chút buffer.
    target_notional = 5.10

    qty = math.ceil(target_notional / price)

    # Round UP theo lot size
    qty = math.ceil(qty / ss.bybit_lot_size) * ss.bybit_lot_size

    notional = price * qty

    print("\nOrder:")
    print("  Side     : Buy")
    print(f"  Price    : {price}")
    print(f"  Qty      : {qty}")
    print(f"  Notional : {notional:.4f} USDT")

    print("\nGửi lệnh LIVE trên Bybit MAINNET? gõ YES để tiếp tục: ", end="")
    confirmation = input().strip()

    if confirmation != "YES":
        print("Cancelled by user.")
        return

    order = Order(ss)

    try:
        print("\n>>> Sending BUY PostOnly order...")

        response = await order.order_limit(
            ("Buy", price, qty)
        )

        print("Response:")
        print(response)

        if response and response.get("return", {}).get("orderId"):
            order_id = response["return"]["orderId"]

            print("\n================================")
            print("ORDER ACCEPTED")
            print("================================")
            print(f"Order ID : {order_id}")
            print(f"Price    : {price}")
            print(f"Qty      : {qty}")
            print(f"Notional : {notional:.4f} USDT")

            print("\nLệnh đang nằm trên Bybit.")
            print("Bạn tự cancel trên web khi muốn.")

        else:
            print("\n================================")
            print("ORDER NOT ACCEPTED")
            print("================================")

    finally:
        await order.session.close()


if __name__ == "__main__":
    asyncio.run(main())
