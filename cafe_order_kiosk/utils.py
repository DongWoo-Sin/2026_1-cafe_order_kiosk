# cafe_order_kiosk/utils.py

def parse_command(command_str: str) -> tuple[str, list[str]]:
    """명령어 문자열을 파싱하여 (명령어, 인자_리스트) 형태로 반환합니다."""
    tokens = command_str.strip().split()
    if not tokens:
        return "", []

    # 띄어쓰기가 포함된 명령어 예외 처리 ("주문 생성", "주문목록 목록" 등)
    if (
        len(tokens) >= 2
        and tokens[0] in ["주문", "주문목록"]
        and tokens[1] in ["생성", "선택", "추가", "삭제", "취소", "목록"]
    ):
        cmd = f"{tokens[0]} {tokens[1]}"
        args = tokens[2:]
    else:
        cmd = tokens[0]
        args = tokens[1:]

    return cmd, args