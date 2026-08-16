"""Mini NPU의 계산, 데이터 검증, 분석, 성능 측정 로직."""

import time


EPSILON = 1e-9


def mac(pattern, filter_values):
    """패턴과 필터의 같은 위치를 곱해 더한 MAC 점수 반환"""
    total = 0

    for row in range(len(pattern)):
        for col in range(len(pattern[0])):
            total += pattern[row][col] * filter_values[row][col]

    return total


def flatten_matrix(matrix):
    """2차원 배열을 행 순서대로 읽어 1차원 배열로 반환"""
    flattened = []

    for row in matrix:
        for value in row:
            flattened.append(value)

    return flattened


def mac_flat(flat_pattern, flat_filter_values):
    """길이가 같은 1차원 배열 두 개의 MAC 점수 반환"""
    if len(flat_pattern) != len(flat_filter_values):
        raise ValueError("패턴과 필터의 길이가 같아야 합니다")

    total = 0
    # 2차원 MAC의 row, col 대신 하나의 index로
    for index in range(len(flat_pattern)):
        total += flat_pattern[index] * flat_filter_values[index]

    return total


def compare_mac_performance(pattern, filter_values, repeat_count=10):
    """같은 입력으로 2차원 MAC과 1차원 MAC의 평균 시간 비교"""
    if isinstance(repeat_count, bool) or not isinstance(repeat_count, int):
        raise ValueError("반복 횟수는 1 이상의 정수여야 합니다")
    if repeat_count < 1:
        raise ValueError("반복 횟수는 1 이상의 정수여야 합니다")

    # 변환 시간을 제외하고 MAC 접근 방식만 비교하도록
    flat_pattern = flatten_matrix(pattern)
    flat_filter_values = flatten_matrix(filter_values)

    two_dimensional_total_seconds = 0.0
    two_dimensional_score = 0
    for _ in range(repeat_count):
        start_time = time.perf_counter()
        two_dimensional_score = mac(pattern, filter_values)
        end_time = time.perf_counter()
        two_dimensional_total_seconds += end_time - start_time

    # 같은 입력과 반복 횟수로 1차원 MAC도 측정
    flat_total_seconds = 0.0
    flat_score = 0
    for _ in range(repeat_count):
        start_time = time.perf_counter()
        flat_score = mac_flat(flat_pattern, flat_filter_values)
        end_time = time.perf_counter()
        flat_total_seconds += end_time - start_time

    return {
        "two_dimensional_score": two_dimensional_score,
        "flat_score": flat_score,
        "repeats": repeat_count,
        "operations": len(flat_pattern),
        "two_dimensional_average_ms": (
            two_dimensional_total_seconds * 1000 / repeat_count
        ),
        "flat_average_ms": flat_total_seconds * 1000 / repeat_count,
    }


def compare_scores(score_a, score_b, epsilon=EPSILON):
    """두 점수를 비교해 A, B, UNDECIDED 중 하나를 반환"""
    if abs(score_a - score_b) < epsilon:
        return "UNDECIDED"
    if score_a > score_b:
        return "A"
    return "B"


def validate_numeric_matrix(values, size, name):
    """배열의 크기와 숫자 여부 확인"""
    if not isinstance(values, list):
        raise ValueError(f"{name}은 2차원 배열이어야 합니다")

    if len(values) != size:
        raise ValueError(
            f"{name} 크기 오류: 행은 {size}개가 필요하지만 "
            f"{len(values)}개입니다"
        )

    for row_index, row in enumerate(values, start=1):
        if not isinstance(row, list):
            raise ValueError(f"{name} {row_index}행은 배열이어야 합니다")

        if len(row) != size:
            raise ValueError(
                f"{name} 크기 오류: {row_index}행의 열은 "
                f"{size}개가 필요하지만 {len(row)}개입니다"
            )

        for col_index, value in enumerate(row, start=1):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(
                    f"{name} {row_index}행 {col_index}열의 값은 숫자여야 합니다"
                )


def normalize_label(label):
    """대소문자와 주변 공백이 다른 라벨을 Cross 또는 X로 통일"""
    normalize_map = {
        "cross": "Cross",
        "+": "Cross",
        "x": "X",
    }

    if not isinstance(label, str):
        raise ValueError(f"라벨은 문자열이어야 합니다: {label}")

    normalized_label = label.strip().lower()
    if normalized_label not in normalize_map:
        raise ValueError(f"지원하지 않는 라벨입니다: {label}")

    return normalize_map[normalized_label]


def generate_pattern(size, label):
    """크기와 라벨에 맞는 Cross 또는 X 패턴 생성"""
    if isinstance(size, bool) or not isinstance(size, int) or size < 1:
        raise ValueError("패턴 크기는 1 이상의 정수여야 합니다")

    normalized_label = normalize_label(label)
    center_indexes = []

    # 홀수는 가운데가 하나고, 짝수는 가운데가 두 개
    if size % 2 == 0:
        center_indexes.append(size // 2 - 1)
        center_indexes.append(size // 2)
    else:
        center_indexes.append(size // 2)

    pattern = []
    # N x N의 모든 좌표를 확인
    for row_index in range(size):
        row = []
        for col_index in range(size):
            if normalized_label == "Cross":
                # 가운데 행 또는 가운데 열에 있으면 Cross 위치
                is_pattern_position = (
                    row_index in center_indexes
                    or col_index in center_indexes
                )
            else:
                # 두 대각선 중 하나에 있으면 X 위치
                is_pattern_position = (
                    row_index == col_index
                    or row_index + col_index == size - 1
                )

            # 패턴에 포함되는 좌표는 1, 나머지는 0으로
            row.append(1 if is_pattern_position else 0)

        pattern.append(row)

    return pattern


def extract_pattern_size(pattern_key):
    """size_{N}_{idx} 형식의 이름에서 배열 크기 N 추출"""
    if not isinstance(pattern_key, str):
        raise ValueError(f"패턴 키는 문자열이어야 합니다: {pattern_key}")

    parts = pattern_key.split("_")
    if len(parts) != 3 or parts[0] != "size":
        raise ValueError(
            f"패턴 키 형식 오류: {pattern_key} "
            "(size_{N}_{idx} 여야 합니다.)"
        )

    if not parts[1].isdigit() or not parts[2].isdigit():
        raise ValueError(
            f"패턴 키 형식 오류: {pattern_key} "
            "(N과 idx는 0 이상의 정수여야 합니다)"
        )

    size = int(parts[1])
    if size <= 0:
        raise ValueError(f"패턴 크기 N은 1 이상이어야 합니다: {pattern_key}")

    return size


def get_filters_for_size(filters, size):
    """크기에 맞는 Cross와 X 필터 반환"""
    filter_key = f"size_{size}"
    # 각 키, 필터 등은 참조 전에 검증 먼저
    if filter_key not in filters:
        raise ValueError(f"필터 누락: {filter_key}")

    raw_filters = filters[filter_key]
    if not isinstance(raw_filters, dict):
        raise ValueError(f"filters.{filter_key}는 JSON 객체여야 합니다")

    normalized_filters = {
        normalize_label(label): values
        for label, values in raw_filters.items()
    }

    # 필수 라벨 체크
    for required_label in ("Cross", "X"):
        if required_label not in normalized_filters:
            raise ValueError(f"{filter_key}에 {required_label} 필터가 없습니다")

    return normalized_filters


def extract_json_sections(data):
    """data.json의 기본 구조를 확인하고 filters와 patterns 반환"""
    # 검증 먼저
    if not isinstance(data, dict):
        raise ValueError("data.json의 최상위 값은 JSON 객체여야 합니다")
    if "filters" not in data:
        raise ValueError("data.json에 filters 키가 없습니다")
    if "patterns" not in data:
        raise ValueError("data.json에 patterns 키가 없습니다")

    filters = data["filters"]
    patterns = data["patterns"]
    if not isinstance(filters, dict):
        raise ValueError("filters는 JSON 객체여야 합니다")
    if not isinstance(patterns, dict):
        raise ValueError("patterns는 JSON 객체여야 합니다")

    return filters, patterns


def analyze_case(pattern_key, case_data, filters):
    """JSON 케이스 하나를 검사하고 점수와 PASS/FAIL 결과 반환"""
    size = extract_pattern_size(pattern_key)

    # 검증 먼저
    if not isinstance(case_data, dict):
        raise ValueError(f"{pattern_key} 케이스는 JSON 객체여야 합니다")
    if "input" not in case_data:
        raise ValueError(f"{pattern_key}에 input 키가 없습니다")
    if "expected" not in case_data:
        raise ValueError(f"{pattern_key}에 expected 키가 없습니다")

    expected = normalize_label(case_data["expected"])
    filters_for_size = get_filters_for_size(filters, size)
    pattern = case_data["input"]

    validate_numeric_matrix(pattern, size, "패턴")
    validate_numeric_matrix(filters_for_size["Cross"], size, "Cross 필터")
    validate_numeric_matrix(filters_for_size["X"], size, "X 필터")

    cross_score = mac(pattern, filters_for_size["Cross"])
    x_score = mac(pattern, filters_for_size["X"])

    compare_result = compare_scores(cross_score, x_score)
    if compare_result == "A":
        prediction = "Cross"
    elif compare_result == "B":
        prediction = "X"
    else:
        prediction = "UNDECIDED"

    status = "PASS" if prediction == expected else "FAIL"
    result = {
        "pattern_key": pattern_key,
        "size": size,
        "cross_score": cross_score,
        "x_score": x_score,
        "prediction": prediction,
        "expected": expected,
        "status": status,
    }

    if status == "FAIL":
        if prediction == "UNDECIDED":
            result["error"] = "동점(UNDECIDED) 처리 규칙에 따라 expected와 불일치"
        else:
            result["error"] = "prediction과 expected가 불일치"

    return result


def analyze_all_cases(patterns, filters):
    """모든 JSON 패턴을 분석하고 전체, 통과, 실패 수 반환"""
    results = []
    passed = 0
    failed = 0

    for pattern_key, case_data in patterns.items():
        try:
            result = analyze_case(pattern_key, case_data, filters)
            results.append(result)
            if result["status"] == "PASS":
                passed += 1
            else:
                failed += 1
        except ValueError as error:
            # 여기서 수많은 에러를 한번에 결과에 추가한다
            results.append({
                "pattern_key": pattern_key,
                "status": "FAIL",
                "error": str(error) or "데이터 형식 오류",
            })
            failed += 1

    return {
        "total": len(patterns),
        "passed": passed,
        "failed": failed,
        "results": results,
    }


def measure_mac(pattern, filter_values):
    """필터 하나의 MAC을 10회 실행해 평균 시간과 결과 반환"""
    repeat_count = 10
    total_elapsed_seconds = 0.0
    score = 0
    operations = len(pattern) * len(pattern[0])

    for _ in range(repeat_count):
        start_time = time.perf_counter()
        score = mac(pattern, filter_values)

        # 경과 시간 : end_time - start_time
        end_time = time.perf_counter()
        total_elapsed_seconds += end_time - start_time

    return {
        "score": score,
        "repeats": repeat_count,
        "mac_calls": repeat_count,
        "operations": operations,
        "average_ms": (total_elapsed_seconds * 1000) / repeat_count,
    }
