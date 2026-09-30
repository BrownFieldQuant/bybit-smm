import asyncio
import aiohttp
import requests

from src.sharedstate import SharedState
from src.exchanges.bybit.post.order import Order


SYMBOL = "THEUSDT"
ORDER_NOTIONAL = 5.2
WAIT_SECONDS = 3


def get_book():
    url = "https://api.bybit.com/v5/market/tickers"

    response = requests.get(
        url,
        params={
            "category": "linear",
            "symbol": SYMBOL,
        },
        timeout=10,
    )
    response.raise_for_status()

    data = response.json()

    if data["retCode"] != 0:
        raise RuntimeError(data)

    ticker = data["result"]["list"][0]

    return (
        float(ticker["bid1Price"]),
        float(ticker["ask1Price"]),
    )


async def main():
    ss = SharedState()

    # Lấy giá hiện tại
    bid, ask = get_book()

    print(f"Symbol : {SYMBOL}")
    print(f"Bid    : {bid}")
    print(f"Ask    : {ask}")

    # THEUSDT có tick = 0.00001, qty step = 1
    tick_size = ss.bybit_tick_size
    qty_step = ss.bybit_lot_size

    # Đặt Buy thấp hơn best bid 1 tick để chắc chắn PostOnly
    price = bid - tick_size

    # Qty sao cho notional khoảng 5.2 USDT
    qty = int(ORDER_NOTIONAL / price)

    # Làm tròn theo qty step
    qty = int(qty / qty_step) * int(qty_step)

    notional = price * qty

    print()
    print("Order:")
    print(f"  Side     : Buy")
    print(f"  Price    : {price}")
    print(f"  Qty      : {qty}")
    print(f"  Notional : {notional:.4f} USDT")

    if notional < 5:
        raise RuntimeError(
            f"Notional {notional:.4f} USDT < Bybit minimum 5 USDT"
        )

    # Safety check
    confirm = input(
        "\nGửi lệnh LIVE trên Bybit MAINNET? gõ YES để tiếp tục: "
    )

    if confirm != "YES":
        print("Cancelled by user.")
        return

    order = Order(ss)

    try:
        print("\n>>> Sending BUY PostOnly order...")

        result = await order.order_limit(
            ("Buy", price, qty)
        )

        print("Response:")
        print(result)

        if not result or result.get("retCode") != 0:
            print("\nOrder was NOT accepted.")
            return

        order_id = (
            result
            .get("result", {})
            .get("orderId")
        )

        if not order_id:
            print("\nWARNING: Cannot find orderId.")
            return

        print(f"\nOrder ID: {order_id}")
        print(f"Waiting {WAIT_SECONDS}s...")

        await asyncio.sleep(WAIT_SECONDS)

        print("\n>>> Cancelling order...")

        cancel_result = await order.cancel(order_id)

        print("Cancel response:")
        print(cancel_result)

        if cancel_result and cancel_result.get("retCode") == 0:
            print("\nSUCCESS: Test order cancelled.")
        else:
            print(
                "\nWARNING: Cancel was not confirmed. "
                "Check open orders on Bybit."
            )

    finally:
        # order._submit() sử dụng ClientSession của Order
        if not order.session.closed:
            await order.session.close()


if __name__ == "__main__":
    asyncio.run(main())
