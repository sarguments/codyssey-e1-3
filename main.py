
def mac(pattern, filter_values):
    """입력 패턴과 필터의 MAC 점수를 반환"""

    total = 0

    # 행 길이 구해서 그 위치의 배열에 접근한다
    row_len = len(pattern)
    col_len = len(pattern[0])

    for row in range(row_len):
        for col in range(col_len):
            total += (pattern[row][col] * filter_values[row][col])

    return total
