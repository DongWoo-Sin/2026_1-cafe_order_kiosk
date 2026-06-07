import sys
from cafe_order_kiosk.kiosk_store import KioskStore
from cafe_order_kiosk.models import Order, OrderStatus
from cafe_order_kiosk.utils import parse_command


class CLIState:
    """CLI의 현재 상태를 유지하는 클래스입니다."""

    def __init__(self) -> None:
        self.current_order_id: int | None = None  # 현재 작업 중인 주문 ID


def format_money(amount: int) -> str:
    """금액을 '1,000원' 형식의 문자열로 변환합니다."""
    return f"{amount:,}원"


def pad_korean(text: str, total_width: int, align: str = "left") -> str:
    """ 한글 전각 문자가 포함된 문자열의 실제 정렬 폭을 계산하여 공백을 채웁니다. """
    # 한글은 터미널에서 2칸을 차지하므로, 문자별 실제 바이트/출력 폭을 계산
    actual_width = sum(2 if ord(char) > 128 else 1 for char in text)
    padding = max(0, total_width - actual_width)
    
    if align == "right":
        return " " * padding + text
    elif align == "center":
        left_pad = padding // 2
        right_pad = padding - left_pad
        return " " * left_pad + text + " " * right_pad
    else:
        return text + " " * padding


# ---------------------------------------------------------
# 출력용 헬퍼 함수들을 handle_pay보다 위에 정의 (NameError 방지)
# ---------------------------------------------------------
def print_number_ticket(order_id: int) -> None:
    """교환권을 화면에 출력합니다."""
    print("\n" + "=" * 40)
    print(pad_korean("교 환 권", 40, "center"))
    print("=" * 40)
    print(f" 대기번호 : {order_id}")
    print("-" * 40)
    print(pad_korean("번호표가 나오면 호출해 드립니다.", 40, "center"))
    print("=" * 40 + "\n")


def print_receipt_doc(order: Order, method: str) -> None:
    """영수증 서식을 화면에 출력합니다."""
    print("\n" + "=" * 40)
    print(pad_korean("영 수 증", 40, "center"))
    print("=" * 40)
    print(f"주문 번호 : #{order.id}")
    print(f"결제 방식 : {method}")
    print("-" * 40)
    
    # 헤더 출력 (한글 정렬 맞춤)
    menu_header = pad_korean("메뉴명", 18, "left")
    qty_header = pad_korean("수량", 6, "left")
    price_header = pad_korean("금액", 12, "right")
    print(f"{menu_header}{qty_header}{price_header}")
    print("-" * 40)
    
    # 각 주문 항목 출력 (실제 models.py 속성인 name, quantity, line_total 사용)
    for item in order.items:
        options = f" ({item.options})" if hasattr(item, 'options') and item.options else ""
        item_title = f"{item.name}{options}"
        
        col_menu = pad_korean(item_title, 18, "left")
        col_qty = pad_korean(f"{item.quantity}개", 6, "left")
        col_price = pad_korean(format_money(item.line_total), 12, "right")
        
        print(f"{col_menu}{col_qty}{col_price}")
        
    print("-" * 40)
    total_label = pad_korean("합계 금액", 24, "left")
    total_val = pad_korean(format_money(order.total_amount), 14, "right")
    print(f"{total_label}{total_val}")
    print("=" * 40 + "\n")


# ---------------------------------------------------------
# 명령어 처리 함수들
# ---------------------------------------------------------
def handle_menu(store: KioskStore, state: CLIState, args: list[str]) -> None:
    print("\n--- 카페 메뉴 목록 ---")
    menus = store.get_all_menus()
    if not menus:
        print("등록된 메뉴가 없습니다.")
        return

    for menu in menus:
        status_str = "" if menu.is_available else " [품절]"
        print(f"[{menu.id}] {menu.name:<12} : {format_money(menu.price)}{status_str}")
    print("----------------------\n")


def handle_order_create(store: KioskStore, state: CLIState, args: list[str]) -> None:
    memo = " ".join(args) if args else None
    order = store.create_order(memo=memo)
    state.current_order_id = order.id
    print(f"▶ 새 주문이 생성되었습니다. (주문 ID: {order.id})")
    if memo:
        print(f"  메모: {memo}")


def handle_order_select(store: KioskStore, state: CLIState, args: list[str]) -> None:
    if not args:
        print("💡 선택할 주문 ID를 입력해주세요. (예: 주문 선택 1)")
        return

    try:
        order_id = int(args[0])
    except ValueError:
        print("❌ 주문 ID는 숫자여야 합니다.")
        return

    order = store.get_order(order_id)
    if not order:
        print(f"❌ 주문 ID {order_id}를 찾을 수 없습니다.")
        return

    state.current_order_id = order.id
    print(f"▶ 주문 #{order.id}가 현재 주문으로 선택되었습니다.")


def handle_order_add(store: KioskStore, state: CLIState, args: list[str]) -> None:
    if not state.current_order_id:
        print("💡 현재 선택된 주문이 없습니다. 먼저 '주문 생성' 또는 '주문 선택 <id>'를 해주세요.")
        return

    if len(args) < 2:
        print("💡 메뉴 ID와 수량을 입력해주세요. (예: 주문 추가 1 2 [샷추가])")
        return

    try:
        menu_id = int(args[0])
        quantity = int(args[1])
    except ValueError:
        print("❌ 메뉴 ID와 수량은 숫자여야 합니다.")
        return

    options = " ".join(args[2:]) if len(args) > 2 else None

    try:
        item = store.add_order_item(state.current_order_id, menu_id, quantity, options)
        print(f"▶ {item.name} {quantity}개가 주문에 추가되었습니다. ({format_money(item.line_total)})")
    except ValueError as e:
        print(f"❌ 오류: {e}")


def handle_order_delete(store: KioskStore, state: CLIState, args: list[str]) -> None:
    if not state.current_order_id:
        print("💡 현재 선택된 주문이 없습니다.")
        return

    if not args:
        print("💡 삭제할 항목의 라인 번호를 입력해주세요. (예: 주문 삭제 1)")
        return

    try:
        line_no = int(args[0])
    except ValueError:
        print("❌ 라인 번호는 숫자여야 합니다.")
        return

    try:
        store.remove_order_item(state.current_order_id, line_no)
        print(f"▶ 주문에서 {line_no}번 항목이 삭제되었습니다.")
    except ValueError as e:
        print(f"❌ 오류: {e}")


def print_order(order: Order) -> None:
    """단일 주문의 상세 내용을 출력합니다."""
    print(f"\n========================================")
    print(f" 주문 번호 : #{order.id}")
    print(f" 상태      : {order.status.value}")
    if order.memo:
        print(f" 메모      : {order.memo}")
    print(f"----------------------------------------")
    if not order.items:
        print(" 주문에 담긴 메뉴가 없습니다.")
    else:
        for item in order.items:
            opt_str = f" ({item.options})" if item.options else ""
            print(f" [{item.line_no}] {item.name}{opt_str:<12} x {item.quantity:<2} : {format_money(item.line_total)}")
    print(f"----------------------------------------")
    print(f" 총 결제금액: {format_money(order.total_amount)}")
    print(f"========================================\n")


def handle_order_view(store: KioskStore, state: CLIState, args: list[str]) -> None:
    if not state.current_order_id:
        print("💡 현재 선택된 주문이 없습니다. '주문 조회'를 하려면 먼저 주문을 생성하거나 선택하세요.")
        return

    order = store.get_order(state.current_order_id)
    if not order:
        print("❌ 현재 선택된 주문 정보를 찾을 수 없습니다.")
        return

    print_order(order)


def handle_order_cancel(store: KioskStore, state: CLIState, args: list[str]) -> None:
    if not state.current_order_id:
        print("💡 현재 선택된 주문이 없습니다.")
        return

    try:
        store.cancel_order(state.current_order_id)
        print(f"▶ 주문 #{state.current_order_id}가 취소되었습니다.")
        state.current_order_id = None
    except ValueError as e:
        print(f"❌ 오류: {e}")


def handle_order_list(store: KioskStore, state: CLIState, args: list[str]) -> None:
    status_filter = None
    if args:
        if args[0] == "진행중":
            status_filter = OrderStatus.PENDING
        elif args[0] == "결제완료":
            status_filter = OrderStatus.PAID
        elif args[0] == "취소":
            status_filter = OrderStatus.CANCELLED

    orders = store.get_all_orders(status_filter=status_filter)
    filter_msg = f" [{args[0]}]" if args else ""
    print(f"\n--- 전체 주문 목록{filter_msg} ---")
    if not orders:
        print("해당하는 주문 내역이 없습니다.")
        return

    for o in orders:
        print(f"#{o.id} [{o.status.value}] 메뉴 {len(o.items)}개 총 {format_money(o.total_amount)}")
    print("-----------------------------\n")


def handle_pay(store: KioskStore, state: CLIState, args: list[str]) -> None:
    if not state.current_order_id:
        print("💡 현재 선택된 주문이 없습니다.")
        return

    order = store.get_order(state.current_order_id)
    if not order:
        print("❌ 주문을 찾을 수 없습니다.")
        return

    if not args:
        print("💡 결제 수단을 입력해주세요. (예: 결제 카드)")
        return

    method = args[0]

    try:
        store.pay_order(order.id, method)
        print(f"▶ 주문 #{order.id} 결제 완료 ({method}).")
        print("-" * 40)
        
        # 1. 번호표 출력 (함수가 위에 선언되어 안전하게 호출됨)
        print_number_ticket(order.id)
        
        # 2. 영수증 선택 출력 인터랙션
        while True:
            receipt_choice = input("영수증을 출력하시겠습니까? (y/n): ").strip().lower()
            if receipt_choice in {"y", "yes"}:
                print_receipt_doc(order, method)
                break
            elif receipt_choice in {"n", "no"}:
                print("영수증을 출력하지 않습니다.")
                break
            else:
                print("❌ 잘못된 입력입니다. y 또는 n을 입력해주세요.")

        # 결제 성공 후 현재 세션 주문 초기화
        state.current_order_id = None

    except ValueError as e:
        print(f"❌ 결제 실패: {e}")


def handle_help(store: KioskStore, state: CLIState, args: list[str]) -> None:
    print("\n====== [ 카페 키오스크 명령어 안내 ] ======")
    print("  메뉴                           - 전체 메뉴판 보기")
    print("  주문 생성 [메모]                - 새로운 주문 바구니 열기")
    print("  주문 선택 <주문_id>             - 이전에 만든 주문 다시 선택하기")
    print("  주문 추가 <메뉴_id> <수량> [옵션] - 현재 바구니에 메뉴 담기")
    print("  주문 삭제 <라인번호>            - 바구니에서 특정 번호 메뉴 빼기")
    print("  주문 조회                      - 현재 내 바구니 상태 보기")
    print("  주문 취소                      - 현재 주문 전체 취소하기")
    print("  주문목록 목록 [진행중|결제완료|취소] - 전체 주문 이력 확인")
    print("  결제 <방법>                    - 현재 주문 결제하고 완료하기")
    print("  도움말                         - 이 안내문 다시 보기")
    print("  종료                           - 키오스크 프로그램 종료")
    print("===========================================\n")


# 명령어 맵핑 사전
COMMAND_MAP = {
    "메뉴": handle_menu,
    "주문 생성": handle_order_create,
    "주문 선택": handle_order_select,
    "주문 추가": handle_order_add,
    "주문 삭제": handle_order_delete,
    "주문 조회": handle_order_view,
    "주문 취소": handle_order_cancel,
    "주문목록 목록": handle_order_list,
    "결제": handle_pay,
    "도움말": handle_help,
}


def run_cli() -> None:
    """CLI 메인 루프를 실행합니다."""
    store = KioskStore()
    state = CLIState()

    print("☕ 안녕하세요! 카페 키오스크 CLI 시스템입니다.")
    print("💡 사용 방법을 보시려면 '도움말'을 입력하세요.")

    while True:
        try:
            prompt_prefix = f"주문 #{state.current_order_id}" if state.current_order_id else "선택 없음"
            user_input = input(f"키오스크({prompt_prefix})> ")
            cmd, args = parse_command(user_input)

            if not cmd:
                continue

            if cmd == "종료":
                print("👋 이용해 주셔서 감사합니다. 프로그램을 종료합니다.")
                break

            if cmd in COMMAND_MAP:
                COMMAND_MAP[cmd](store, state, args)
            else:
                print(f"❌ 알 수 없는 명령어입니다: '{cmd}'. '도움말'을 입력해 보세요.")

        except (KeyboardInterrupt, EOFError):
            print("\n👋 프로그램을 강제 종료합니다.")
            sys.exit(0)