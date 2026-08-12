
import json
import time


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


def validate_numeric_matrix(values, size, name):
    """행렬의 크기와 모든 원소의 숫자 여부를 검증"""
    if not isinstance(values, list):
        raise ValueError(f"{name}은(는) 2차원 배열이어야 합니다")

    if len(values) != size:
        raise ValueError(
            f"{name} 행 수 불일치: {size}개가 필요하지만 {len(values)}개입니다"
        )

    for row_index, row in enumerate(values, start=1):
        if not isinstance(row, list):
            raise ValueError(f"{name} {row_index}행은 배열이어야 합니다")

        if len(row) != size:
            raise ValueError(
                f"{name} {row_index}행 열 수 불일치: "
                f"{size}개가 필요하지만 {len(row)}개입니다"
            )

        for col_index, value in enumerate(row, start=1):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(
                    f"{name} {row_index}행 {col_index}열의 값은 숫자여야 합니다"
                )


def normalize_label(label):
    """JSON 라벨을 Cross 또는 X로 정규화"""
    normalize_map = {
        'cross': 'Cross',
        '+': 'Cross',
        'x': 'X',
    }

    if not isinstance(label, str):
        raise ValueError(f"라벨은 문자열이어야 합니다: {label!r}")
    if label not in normalize_map:
        raise ValueError(f"지원하지 않는 라벨입니다: {label!r}")

    return normalize_map[label]


def extract_pattern_size(pattern_key):
    """size_{N}_{idx} 형식의 패턴 키에서 크기 N을 반환"""
    if not isinstance(pattern_key, str):
        raise ValueError(f"패턴 키는 문자열이어야 합니다: {pattern_key!r}")

    splited = pattern_key.split("_")
    if(len(splited) != 3 or splited[0] != 'size'):
        raise ValueError(
            f"패턴 키 형식 오류: {pattern_key!r} "
            "(예상 형식: size_{N}_{idx})"
        )

    if not splited[1].isdigit() or not splited[2].isdigit():
        raise ValueError(
            f"패턴 키 형식 오류: {pattern_key!r} "
            "(N과 idx는 0 이상의 정수여야 합니다)"
        )

    size = int(splited[1])
    if size <= 0:
        raise ValueError(f"패턴 크기 N은 1 이상이어야 합니다: {pattern_key!r}")

    return size


def get_filters_for_size(filters, size):
    """크기에 맞는 필터를 찾아 Cross/X 표준 라벨로 반환"""
    filter_key = f"size_{size}"
    if filter_key not in filters:
        raise ValueError(f"필터 누락: {filter_key}")

    raw_filters = filters[filter_key]
    if not isinstance(raw_filters, dict):
        raise ValueError(f"filters.{filter_key}는 JSON 객체여야 합니다")

    normalized_filters = {
        normalize_label(label): values
        for label, values in raw_filters.items()
    }

    for required_label in ("Cross", "X"):
        if required_label not in normalized_filters:
            raise ValueError(f"{filter_key}에 {required_label} 필터가 없습니다")

    return normalized_filters


def extract_json_sections(data):
    """JSON 최상위 스키마를 검증하고 filters/patterns를 반환"""
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
    """JSON 패턴 케이스 하나를 분석한 결과를 반환"""
    # 1. 패턴 키에서 크기 N 을 구한다.
    N = extract_pattern_size(pattern_key)

    if not isinstance(case_data, dict):
        raise ValueError(f"{pattern_key} 케이스는 JSON 객체여야 합니다")

    if "input" not in case_data:
        raise ValueError(f"{pattern_key}에 input 키가 없습니다")
    if "expected" not in case_data:
        raise ValueError(f"{pattern_key}에 expected 키가 없습니다")

    # JSON의 cross/x 키도 내부 표준 라벨인 Cross/X로 통일한다.
    use_filters = get_filters_for_size(filters, N)

    # 3. 케이스의 `input`과 필터 두 개가 모두 올바른 정사각형인지 확인한다.
    validate_numeric_matrix(case_data["input"], N, "패턴")
    validate_numeric_matrix(use_filters["Cross"], N, "Cross 필터")
    validate_numeric_matrix(use_filters["X"], N, "X 필터")
    
    # 4. Cross 점수와 X 점수를 구한다.
    cross_score = mac(case_data['input'], use_filters['Cross'])
    x_score = mac(case_data['input'], use_filters['X'])

    # 5. `compare_scores()` 결과 A/B를 Cross/X로 바꾼다. 동점은 UNDECIDED를 유지한다.
    compare_result = compare_scores(cross_score, x_score)
    if compare_result == 'A':
        prediction = 'Cross'
    elif compare_result == 'B':
        prediction = 'X'
    else:
        prediction = 'UNDECIDED'

    # 6. `normalize_label()`로 expected를 표준화한다.
    expected = normalize_label(case_data['expected'])

    # 7. prediction과 expected를 비교해 PASS 또는 FAIL을 정한다.
    final_result = "PASS" if prediction == expected else "FAIL"

    # 8. 테스트에 적힌 키를 가진 결과 딕셔너리를 반환한다.
    result = {
        "pattern_key": pattern_key,
        "size": N,
        "cross_score": cross_score,
        "x_score": x_score,
        "prediction": prediction,
        "expected": expected,
        "status": final_result,
    }

    if final_result == "FAIL":
        if prediction == "UNDECIDED":
            result["error"] = "동점(UNDECIDED) 처리 규칙에 따라 expected와 불일치"
        else:
            result["error"] = "prediction과 expected가 불일치"

    return result

def analyze_all_cases(patterns, filters):
    """모든 JSON 패턴을 분석하고 성공과 실패 요약을 반환"""
    results = []
    passed = 0
    failed = 0

    for k, v in patterns.items():
        try:
            result = analyze_case(k, v, filters)
            results.append(result)

            if result['status'] == 'PASS':
                passed += 1
            else:
                failed += 1
        # 예상 가능한 데이터 오류만 격리하고 프로그래밍 오류는 숨기지 않는다.
        except ValueError as error:
            error_message = str(error) or "데이터 형식 오류"
            results.append({
                    'pattern_key': k,
                    'status': 'FAIL',
                    'error': error_message
                })
            failed += 1

    # 종합 결과 리턴
    return {
        "total": len(patterns),
        "passed": passed,
        "failed": failed,
        "results": results,
    }


def read_matrix(name, size=3):
    """지정한 크기의 숫자 행렬을 입력받고 잘못된 입력은 다시 요청"""
    while True:
        rows = []
        for i in range(size):
            try:
                line = input(f"{name} {i + 1}행 : ")
                splited = line.split()

                if len(splited) != size:
                    raise ValueError

                rows.append([float(item) for item in splited])
            except ValueError:
                print("입력 형식 오류: 각 줄에 3개의 숫자를 공백으로 구분해 입력하세요.")
                # 현재 rows를 버리고 바깥 반복문에서 배열 전체를 다시 받는다.
                break

        if len(rows) == size:
            return rows


def measure_mac(pattern, filter_values):
    """MAC 실행 시간을 반복 측정한 평균과 연산 정보를 반환"""
    repeat_count = 10
    total_elapsed_seconds = 0.0
    score = 0
    operations = len(pattern) * len(pattern[0])

    for _ in range(repeat_count):
        # 입력과 출력은 제외하고 MAC 함수 호출 구간만 측정한다.
        start_time = time.perf_counter()

        score = mac(pattern, filter_values)

        end_time = time.perf_counter()
        total_elapsed_seconds += end_time - start_time

    return {
        "score": score,
        "repeats": repeat_count,
        "operations": operations,
        "average_ms": (total_elapsed_seconds * 1000) / repeat_count,
    }


def run_user_mode():
    """3*3 사용자 입력 모드를 실행"""

    filter_a = read_matrix("필터 A")
    print("필터 A 저장 완료")

    filter_b = read_matrix("필터 B")
    print("필터 B 저장 완료")

    # 3×3 패턴을 입력받는다.
    three_pattern = read_matrix("패턴")

    # A와 B 점수 및 평균 시간을 구한다.
    a_result = measure_mac(three_pattern, filter_a)
    b_result = measure_mac(three_pattern, filter_b)

    # A/B/UNDECIDED를 판정한다.
    decided = compare_scores(a_result["score"], b_result["score"])
    # JSON 모드와 달리 사용자 모드에서는 동점을 한국어로 표시한다.
    display_decision = "판정 불가" if decided == "UNDECIDED" else decided

    # 점수, 판정, 3×3 성능 분석을 출력한다.
    print(f"A 점수: {a_result['score']:.16f}")
    print(f"B 점수: {b_result['score']:.16f}")
    print(f"판정: {display_decision}")

    average_ms = (a_result['average_ms'] + b_result['average_ms']) / 2
    print("성능 분석 (평균/10회)")
    print(
        f"3 x 3: {average_ms:.6f} ms, "
        f"연산 횟수 {a_result['operations']}"
    )


def run_json_mode(data_path="data.json"):
    """JSON 분석 모드를 실행"""

    try:
        with open(data_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        filters, patterns = extract_json_sections(data)
    except OSError as error:
        print(f"data.json 파일 오류: {error}")
        return
    except json.JSONDecodeError as error:
        print(f"data.json JSON 형식 오류: {error}")
        return
    except ValueError as error:
        print(f"data.json 스키마 오류: {error}")
        return

    summary = analyze_all_cases(patterns, filters)

    for result in summary["results"]:
        print(f"케이스: {result['pattern_key']}")

        # 검증 단계에서 실패한 케이스는 MAC을 실행하지 않아 점수 키가 없다.
        if "cross_score" not in result:
            print(f"결과: {result['status']}")
            print(f"실패 사유: {result['error']}")
            continue

        print(f"Cross 점수: {result['cross_score']:.16f}")
        print(f"X 점수: {result['x_score']:.16f}")
        print(f"판정: {result['prediction']}")
        print(f"expected: {result['expected']}")
        print(f"결과: {result['status']}")
        if "error" in result:
            print(f"실패 사유: {result['error']}")

    # data.json에는 3×3 데이터가 없으므로 미션 문제에 있던 Cross 예제를 사용한다.
    sample_3x3 = [
        [0, 1, 0],
        [1, 1, 1],
        [0, 1, 0],
    ]
    # (크기, MAC 측정 결과, 오류 메시지) 형식으로 3×3 성능 결과를 먼저 저장한다.
    # 정상 측정이므로 오류 메시지는 None이다.
    performance_rows = [(3, measure_mac(sample_3x3, sample_3x3), None)]

    for size in (5, 13, 25):
        try:
            performance_key = f"size_{size}_1"
            if performance_key not in patterns:
                raise ValueError(f"성능 측정 케이스 누락: {performance_key}")

            performance_case = patterns[performance_key]
            if not isinstance(performance_case, dict):
                raise ValueError(f"{performance_key} 케이스는 JSON 객체여야 합니다")
            if "input" not in performance_case:
                raise ValueError(f"{performance_key}에 input 키가 없습니다")

            pattern = performance_case["input"]
            normalized_filters = get_filters_for_size(filters, size)
            cross_filter = normalized_filters["Cross"]
            validate_numeric_matrix(pattern, size, f"size_{size}_1 패턴")
            validate_numeric_matrix(cross_filter, size, f"size_{size} Cross 필터")
            performance_rows.append(
                (size, measure_mac(pattern, cross_filter), None)
            )
        # 한 크기의 데이터가 잘못돼도 나머지 성능과 결과 요약은 출력한다.
        except ValueError as error:
            performance_rows.append((size, None, str(error)))

    print("성능 분석 (평균/10회)")
    for size, performance, error in performance_rows:
        if error is not None:
            print(f"{size} x {size}: 측정 불가 ({error})")
            continue

        print(
            f"{size} x {size}: "
            f"{performance['average_ms']:.6f} ms, "
            f"연산 횟수 {performance['operations']}"
        )

    print("결과 요약")
    print(f"전체: {summary['total']}")
    print(f"통과: {summary['passed']}")
    print(f"실패: {summary['failed']}")

    if summary["failed"]:
        print("실패 케이스:")
        for result in summary["results"]:
            if result["status"] == "FAIL":
                print(f"- {result['pattern_key']}: {result['error']}")


def main():
    """실행 모드를 선택해 Mini NPU 프로그램을 실행"""
    while True:
        print("1. 사용자 입력 (3 x 3)")
        print("2. data.json 분석")
        choice = input("선택: ")

        if choice == "1":
            run_user_mode()
            return

        if choice == "2":
            run_json_mode()
            return

        print("선택 오류: 1 또는 2를 입력하세요.")


if __name__ == "__main__":
    main()
