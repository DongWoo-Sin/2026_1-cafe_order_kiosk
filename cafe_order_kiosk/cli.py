from __future__ import annotations

import shlex
from dataclasses import dataclass

from cafe_order_kiosk.models import OrderStatus
from cafe_order_kiosk.kiosk_store import KioskStore
from cafe_order_kiosk.utils import format_money


@dataclass
class CLIState:
    current_order_id: int | None = None


def run_cli() -> int:
    store = KioskStore.with_default_menu()
    state = CLIState()

    print("카페 주문 키오스크")
    print("명령어 목록은 '도움말'을 입력하세요. 가격은 원 단위 정수입니다.")

    while True:
        try:
            raw = input("kiosk> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not raw:
            continue

        tokens = shlex.split(raw)
        command, args = tokens[0], tokens[1:]

        if command in {"종료", "끝", "quit", "exit"}:
            break
        elif command in {"도움말", "help"}:
            print_help()
        elif command in {"메뉴", "menu"}:
            handle_menu(store)
        elif command in {"주문", "order"}:
            handle_order(store, state, args)
        elif command in {"주문목록", "orders"}:
            handle_orders(store, args)
        elif command in {"결제", "pay"}:
            handle_pay(store, state, args)
        else:
            print("알 수 없는 명령입니다. '도움말'을 입력하세요.")
    print("종료합니다.")
    return 0


def print_help() -> None:
    print("명령어:")
    print("\t메뉴")
    print("\t주문 생성 [메모]")
    print("\t주문 선택 <주문_id>")
    print("\t주문 추가 <메뉴_id> <수량> [옵션]")
    print("\t주문 삭제 <라인번호>")
    print("\t주문 조회")
    print("\t주문 취소")
    print("\t주문목록 목록 [진행중|결제완료|취소]")
    print("\t결제 <방법> [금액]")
    print("\t도움말")
    print("\t종료")


def handle_menu(store: KioskStore) -> None:
    print("메뉴:")
    for item in store.list_menu():
        description = f" - {item.description}" if item.description else ""
        print(
            f"\t{item.id}. {item.name} ({item.category}) - {format_money(item.price)}"
            f"{description}"
        )


def handle_order(store: KioskStore, state: CLIState, args: list[str]) -> None:
    if not args:
        print("주문 명령어: 생성, 선택, 추가, 삭제, 조회, 취소")
        return

    action, tail = args[0], args[1:]

    if action in {"생성", "new"}:
        note = " ".join(tail).strip() if tail else None
        order = store.create_order(note=note)
        state.current_order_id = order.id
        print(f"주문 #{order.id}가 생성되었습니다.")
    elif action in {"선택", "select"}:
        order_id = parse_int_arg(tail, "order_id")
        if order_id is None:
            return
        order = store.get_order(order_id)
        if order is None:
            print("주문을 찾을 수 없습니다.")
            return
        state.current_order_id = order.id
        print(f"주문 #{order.id}를 선택했습니다.")
    elif action in {"추가", "add"}:
        if state.current_order_id is None:
            print("선택된 주문이 없습니다. 먼저 '주문 생성'을 사용하세요.")
            return
        if len(tail) < 2:
            print("사용법: 주문 추가 <메뉴_id> <수량> [옵션]")
            return
        menu_id = parse_int_arg(tail[:1], "menu_id")
        quantity = parse_int_arg(tail[1:2], "qty")
        if menu_id is None or quantity is None:
            return

        options_text = " ".join(tail[2:]).strip()
        options = (
            [option.strip() for option in options_text.split(",") if option.strip()]
            if options_text
            else []
        )
        try:
            store.add_item(state.current_order_id, menu_id, quantity, options)
        except ValueError as exc:
            print(str(exc))
            return
        print("항목이 추가되었습니다.")
    elif action in {"삭제", "remove"}:
        if state.current_order_id is None:
            print("선택된 주문이 없습니다. 먼저 '주문 생성'을 사용하세요.")
            return
        line_index = parse_int_arg(tail, "line_index")
        if line_index is None:
            return
        try:
            store.remove_item(state.current_order_id, line_index)
        except ValueError as exc:
            print(str(exc))
            return
        print("항목이 삭제되었습니다.")
    elif action in {"조회", "show"}:
        if state.current_order_id is None:
            print("선택된 주문이 없습니다. 먼저 '주문 생성'을 사용하세요.")
            return
        order = store.get_order(state.current_order_id)
        if order is None:
            print("주문을 찾을 수 없습니다.")
            return
        print_order(order)
    elif action in {"취소", "cancel"}:
        if state.current_order_id is None:
            print("선택된 주문이 없습니다. 먼저 '주문 생성'을 사용하세요.")
            return
        try:
            order = store.cancel_order(state.current_order_id)
        except ValueError as exc:
            print(str(exc))
            return
        print(f"주문 #{order.id}가 취소되었습니다.")
    else:
        print("알 수 없는 주문 명령어입니다.")


def handle_orders(store: KioskStore, args: list[str]) -> None:
    if not args or args[0] not in {"list", "목록"}:
        print("사용법: 주문목록 목록 [진행중|결제완료|취소]")
        return

    status = None
    if len(args) > 1:
        status = parse_status(args[1])
        if status is None:
            return

    orders = store.list_orders(status)
    if not orders:
        print("주문이 없습니다.")
        return

    for order in orders:
        print(
            f"  #{order.id} {format_status(order.status)} - {format_money(order.total)}"
        )


# =====================================================================
# 이 부분을 요구사항에 맞춰 전면 수정했습니다.
# =====================================================================
def handle_pay(store: KioskStore, state: CLIState, args: list[str]) -> None:
    if state.current_order_id is None:
        print("선택된 주문이 없습니다. 먼저 '주문 생성'을 사용하세요.")
        return
    if not args:
        print("사용법: 결제 <방법> [금액]")
        return

    method = args[0]
    amount = None
    if len(args) > 1:
        amount = parse_int_arg(args[1:2], "amount")
        if amount is None:
            return

    order = store.get_order(state.current_order_id)
    if order is None:
        print("주문을 찾을 수 없습니다.")
        return
    if amount is None:
        amount = order.total

    try:
        store.pay_order(order.id, method, amount)
    except ValueError as exc:
        print(str(exc))
        return

    print(f"주문 #{order.id} 결제 완료 ({method}).")
    print("-" * 40)

    # 1. 번호표 출력 (무조건 실행)
    print_number_ticket(order.id)

    # 2. 영수증 출력 선택 (Y / N)
    while True:
        receipt_choice = input("영수증을 출력하시겠습니까? (y/n): ").strip().lower()
        if receipt_choice in {"y", "yes"}:
            print_receipt_doc(order, method)
            break
        elif receipt_choice in {"n", "no"}:
            print("영수증 출력을 취소했습니다.")
            break
        else:
            print("잘못된 입력입니다. y 또는 n을 입력해 주세요.")
            
    print("-" * 40)


def print_order(order) -> None:
    print(f"주문 #{order.id} ({format_status(order.status)})")
    if order.note:
        print(f"메모: {order.note}")
    if not order.items:
        print("  (비어 있음)")
        return

    for idx, item in enumerate(order.items, start=1):
        options = f" [{', '.join(item.options)}]" if item.options else ""
        print(
            f"  {idx}. {item.name}{options} x{item.quantity}"
            f" - {format_money(item.line_total)}"
        )
    print(f"합계: {format_money(order.total)}")


def parse_int_arg(args: list[str], name: str) -> int | None:
    if not args:
        print(f"필수 값이 없습니다: {name}")
        return None
    try:
        return int(args[0])
    except ValueError:
        print(f"잘못된 값: {name}")
        return None


def parse_status(raw: str) -> OrderStatus | None:
    normalized = raw.lower()
    status_map = {
        "open": OrderStatus.OPEN,
        "paid": OrderStatus.PAID,
        "canceled": OrderStatus.CANCELED,
        "진행중": OrderStatus.OPEN,
        "결제완료": OrderStatus.PAID,
        "취소": OrderStatus.CANCELED,
    }
    status = status_map.get(normalized)
    if status is None:
        print("잘못된 상태입니다. 진행중, 결제완료, 취소 중에서 선택하세요.")
    return status

def format_status(status: OrderStatus) -> str:
    status_map = {
        OrderStatus.OPEN: "진행중",
        OrderStatus.PAID: "결제완료",
        OrderStatus.CANCELED: "취소",
    }
    return status_map.get(status, status.value)


# =====================================================================
# 새로 추가된 번호표 및 영수증 포맷팅 함수들입니다.
# =====================================================================
def print_number_ticket(order_id: int) -> None:
    """번호표를 무조건 출력합니다."""
    print("\n┌──────────────────────────────────────┐")
    print("│             🔔 대기 번호표            │")
    print("├──────────────────────────────────────┤")
    print(f"│                                      │")
    print(f"│          고객님의 대기번호           │")
    print(f"│                 [{order_id:03d}]                │")
    print(f"│                                      │")
    print("│    주문이 완료되면 안내해 드립니다.  │")
    print("└──────────────────────────────────────┘\n")


def print_receipt_doc(order, method: str) -> None:
    """선택 시 영수증 서식을 출력합니다."""
    print("\n========================================")
    print("               🧾 영 수 증              ")
    print("========================================")
    print(f" 주문 번호 : #{order.id}")
    print(f" 결제 방식 : {method}")
    if order.note:
        print(f" 메모 사항 : {order.note}")
    print("----------------------------------------")
    print(" 상품명             수량            금액")
    print("----------------------------------------")
    
    for item in order.items:
        options = f" ({', '.join(item.options)})" if item.options else ""
        item_title = f"{item.name}{options}"
        # 한글 정렬 공백 맞춤이 어려울 수 있으므로 기본 간격 출력
        print(f" {item_title:<16}  x{item.quantity:<4}  {format_money(item.line_total):>10}")
        
    print("----------------------------------------")
    print(f" 합계 금액 : {format_money(order.total):>26}")
    print("========================================")
    print("        이용해 주셔서 감사합니다!       ")
    print("========================================\n")