import asyncio

from src.sharedstate import SharedState
from src.exchanges.bybit.post.order import Order


async def main():
    ss = SharedState()
    order = Order(ss)

    order_id = input("Nhập Order ID cần cancel: ").strip()

    if not order_id:
        print("Order ID rỗng.")
        await order.session.close()
        return

    print(f"\n>>> Cancelling order: {order_id}")

    try:
        response = await order.cancel(order_id)

        print("\nResponse:")
        print(response)

        if response and response.get("return"):
            print("\n================================")
            print("CANCEL REQUEST SENT")
            print("================================")
        else:
            print("\n================================")
            print("CANCEL FAILED")
            print("================================")

    finally:
        await order.session.close()


if __name__ == "__main__":
    asyncio.run(main())
