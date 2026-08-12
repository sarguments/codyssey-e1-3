
EPSILON = 1e-9


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


def compare_scores(score_a, score_b, epsilon=EPSILON):
    """두 점수를 비교해 A, B or UNDECIDED를 반환"""
    abs_diff = abs(score_a - score_b)
    if abs_diff < epsilon:
        return "UNDECIDED"
    elif score_a > score_b:
        return "A"
    else:
        return "B"


def is_square_matrix(values, size):
    """값이 지정한 크기의 2차원 정사각형 배열인지 반환"""
    # 행 갯수와 열 갯수 같은지 확인

    if len(values) != size:
        return False

    for row in values:
        if len(row) != size:
            return False

    return True


def normalize_label(label):
    """여러 형태의 라벨을 Cross 또는 X로 정규화"""
    normalize_map = {
        'CROSS': 'Cross',
        'Cross': 'Cross',
        'cross': 'Cross',
        '+': 'Cross',
        'X': 'X',
        'x': 'X',
    }

    return normalize_map[label]


def extract_pattern_size(pattern_key):
    """size_{N}_{idx} 형식의 패턴 키에서 크기 N을 반환"""
    splited = pattern_key.split("_")
    if(len(splited) != 3 or splited[0] != 'size'):
        raise ValueError

    if not splited[1].isdigit() or not splited[2].isdigit():
        raise ValueError

    return int(splited[1])
