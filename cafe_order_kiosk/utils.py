from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def format_money(amount: int) -> str:
    return f"{amount:,}"

def print_receipt(order):
    """영수증 출력 (선택 기능)"""
    print("\n==============================")
    print("         🧾 영 수 증          ")
    print("==============================")
    print(def_order_info(order)) # 주문 번호, 일시 등
    print("------------------------------")
    for item in order.items:
        print(f"{item.menu_name:<10} {item.quantity}개  {item.price:,}원")
    print("------------------------------")
    print(f"합계 금액: {order.total_amount:,}원")
    print("==============================\n")

def print_number_ticket(order_id):
    """번호표 출력 (필수 기능)"""
    print("\n==============================")
    print("         🔔 대기 번호표        ")
    print("==============================")
    print(f"\n      고객님의 대기번호      ")
    print(f"           [{order_id}]       \n")
    print("  음식이 완료되면 불러드리겠습니다. ")
    print("==============================\n")