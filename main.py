"""Mini NPU 콘솔 입출력과 실행 메뉴."""

import json

from npu import (
    analyze_all_cases,
    compare_mac_performance,
    compare_scores,
    extract_json_sections,
    generate_pattern,
    get_filters_for_size,
    mac,
    measure_mac,
    validate_numeric_matrix,
)


def read_matrix(name, size=3):
    """숫자 배열을 입력받고 잘못되면 처음부터 다시 입력"""
    while True:
        rows = []
        for row_index in range(size):
            try:
                line = input(f"{name} {row_index + 1}행: ")
                values = line.split()

                if len(values) != size:
                    raise ValueError

                rows.append([float(value) for value in values])
            except ValueError:
                print(
                    "입력 형식 오류: "
                    f"각 줄에 {size}개의 숫자를 공백으로 구분해 입력하세요."
                )
                break

        if len(rows) == size:
            return rows


def read_positive_int(prompt):
    """1 이상의 정수를 입력받고 잘못되면 다시 입력"""
    while True:
        try:
            value = int(input(prompt))
        except ValueError:
            print("입력 오류: 1 이상의 정수를 입력하세요.")
            continue

        if value < 1:
            print("입력 오류: 1 이상의 정수를 입력하세요.")
            continue

        return value


def read_generated_pattern(size):
    """지원하는 라벨을 입력받아 지정한 크기의 패턴 생성"""
    while True:
        label = input("패턴 종류 (Cross/X): ")
        try:
            return generate_pattern(size, label)
        except ValueError as error:
            print(f"입력 오류: {error}")


def read_pattern_for_user_mode(size=3):
    """사용자 모드의 패턴을 직접 입력하거나 자동 생성"""
    while True:
        print("[패턴 입력 방식]")
        print("1. 직접 입력")
        print("2. Cross/X 자동 생성")
        choice = input("선택: ")

        if choice == "1":
            return read_matrix("패턴", size)

        if choice == "2":
            pattern = read_generated_pattern(size)
            print("")
            print(f"생성된 {size} x {size} 패턴")
            print_pattern(pattern)
            return pattern

        print("선택 오류: 1 또는 2를 입력하세요.")


def print_mac_performance_table(performance_rows):
    """필터 하나의 MAC 성능을 출력"""
    for row in performance_rows:
        size = row["size"]
        performance = row["performance"]
        error = row["error"]
        if error is not None:
            print(f"{size} x {size}: 측정 불가: {error}")
            continue

        print(f"크기: {size} x {size}")
        print(f"평균 MAC 시간: {performance['average_ms']:.6f} ms")
        print(f"MAC 연산 횟수(N²): {performance['operations']}")


def print_pattern(pattern):
    """생성한 패턴을 행 단위로 출력"""
    for row in pattern:
        print(" ".join(str(value) for value in row))


def print_mac_comparison(comparison):
    """2차원 접근과 1차원 접근의 MAC 성능 비교 출력"""
    print(f"반복 횟수: {comparison['repeats']}")
    print(f"MAC 연산 횟수(N²): {comparison['operations']}")
    print(
        "2차원 배열 평균 MAC 시간: "
        f"{comparison['two_dimensional_average_ms']:.6f} ms"
    )
    print(
        "1차원 배열 평균 MAC 시간: "
        f"{comparison['flat_average_ms']:.6f} ms"
    )


def run_user_mode():
    """직접 입력한 3x3 필터 두 개와 패턴 계산"""
    filter_a = read_matrix("필터 A")
    print("필터 A 저장 완료\n")

    filter_b = read_matrix("필터 B")
    print("필터 B 저장 완료\n")

    # 직접 입력뿐 아니라 패턴 생성기의 3 x 3 결과도 같은 계산에 사용한다.
    pattern = read_pattern_for_user_mode(size=3)
    filter_a_performance = measure_mac(pattern, filter_a)
    filter_b_score = mac(pattern, filter_b)
    decision = compare_scores(
        filter_a_performance["score"],
        filter_b_score,
    )
    # 사용자 모드에서만 'UNDECIDED' 대신 '판정 불가'
    display_decision = "판정 불가" if decision == "UNDECIDED" else decision

    print("")
    print(f"A 점수: {filter_a_performance['score']:.16f}")
    print(f"B 점수: {filter_b_score:.16f}")
    print(f"판정: {display_decision}")

    print("")
    print("성능 분석 (필터 A의 MAC 10회 평균)")
    performance_rows = [{
        "size": 3,
        "performance": filter_a_performance,
        "error": None,
    }]
    print_mac_performance_table(performance_rows)


def run_json_mode(data_path="data.json"):
    """data.json의 패턴을 분석하고 결과와 성능 출력"""
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

    for index, result in enumerate(summary["results"]):
        if index > 0:
            print("")
        print(f"케이스: {result['pattern_key']}")

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

    # 기본 data.json 에 3x3 이 존재하지 않아 예제에 있던 3x3 사용
    sample_3x3 = [
        [0, 1, 0],
        [1, 1, 1],
        [0, 1, 0],
    ]
    mac_performance_rows = [{
        "size": 3,
        "performance": measure_mac(sample_3x3, sample_3x3),
        "error": None,
    }]

    # 3x3은 위의 예제 행렬로 이미 측정했으므로, data.json에 준비된
    # 나머지 크기(5x5, 13x13, 25x25)의 첫 번째 케이스로 성능을 비교한다.
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

            # 성능 분석 (Cross MAC 10회 평균)
            mac_performance_rows.append({
                "size": size,
                "performance": measure_mac(pattern, cross_filter),
                "error": None,
            })
        except ValueError as error:
            error_row = {
                "size": size,
                "performance": None,
                "error": str(error),
            }
            mac_performance_rows.append(error_row)

    print("")
    print("성능 분석 (필터 하나의 MAC 10회 평균)")
    print_mac_performance_table(mac_performance_rows)

    print("")
    print("결과 요약")
    print(f"전체: {summary['total']}")
    print(f"통과: {summary['passed']}")
    print(f"실패: {summary['failed']}")

    if summary["failed"]:
        print("실패 케이스:")
        for result in summary["results"]:
            if result["status"] == "FAIL":
                print(f"- {result['pattern_key']}: {result['error']}")


def run_pattern_generator_mode():
    """Cross 또는 X 패턴을 만들고 두 MAC 접근 방식 비교"""
    size = read_positive_int("패턴 크기 N: ")
    pattern = read_generated_pattern(size)

    print("")
    print(f"생성된 {size} x {size} 패턴")
    print_pattern(pattern)

    # 생성한 패턴을 입력과 필터로 함께 사용해 두 MAC의 접근 방식만 비교
    comparison = compare_mac_performance(pattern, pattern)
    print("")
    print("메모리 접근 방식별 MAC 성능 비교")
    print_mac_comparison(comparison)


def main():
    """종료할 때까지 Mini NPU의 세 모드를 반복 실행"""
    print("=== Mini NPU Simulator ===")
    while True:
        print("")
        print("[모드 선택]")
        print("1. 사용자 입력 (3 x 3)")
        print("2. data.json 분석")
        print("3. 패턴 생성기와 MAC 최적화 비교")
        print("0. 종료")
        choice = input("선택: ")

        if choice == "1":
            run_user_mode()
            continue
        if choice == "2":
            run_json_mode()
            continue
        if choice == "3":
            run_pattern_generator_mode()
            continue
        if choice == "0":
            print("프로그램을 종료합니다.")
            return

        print("선택 오류: 0, 1, 2 또는 3을 입력하세요.")


if __name__ == "__main__":
    main()
