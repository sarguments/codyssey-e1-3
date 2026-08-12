"""Mini NPU 콘솔 입출력과 실행 메뉴."""

import json

from npu import (
    analyze_all_cases,
    extract_json_sections,
    get_filters_for_size,
    measure_classification,
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


def print_mac_performance_table(performance_rows):
    """필터 하나의 MAC 성능을 출력"""
    for size, performance, error in performance_rows:
        if error is not None:
            print(f"{size} x {size}: 측정 불가: {error}")
            continue

        print(f"크기: {size} x {size}")
        print(f"평균 MAC 시간: {performance['average_ms']:.6f} ms")
        print(f"MAC 연산 횟수(N²): {performance['operations']}")


def print_classification_performance_table(performance_rows):
    """두 필터를 사용하는 전체 판정 성능을 출력"""
    for size, performance, error in performance_rows:
        if error is not None:
            print(f"{size} x {size}: 측정 불가: {error}")
            continue

        print(f"크기: {size} x {size}")
        print(f"평균 판정 시간: {performance['average_ms']:.6f} ms")
        print(f"위치별 MAC/판정(2N²): {performance['operations']}")


def run_user_mode():
    """직접 입력한 3x3 필터 두 개와 패턴 계산"""
    filter_a = read_matrix("필터 A")
    print("필터 A 저장 완료\n")

    filter_b = read_matrix("필터 B")
    print("필터 B 저장 완료\n")

    pattern = read_matrix("패턴")
    performance = measure_classification(pattern, filter_a, filter_b)
    decision = performance["decision"]
    display_decision = "판정 불가" if decision == "UNDECIDED" else decision

    print("")
    print(f"A 점수: {performance['score_a']:.16f}")
    print(f"B 점수: {performance['score_b']:.16f}")
    print(f"판정: {display_decision}")

    print("")
    print("성능 분석 (판정 10회, MAC 호출 총 20회)")
    print_classification_performance_table([(3, performance, None)])


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

    sample_3x3 = [
        [0, 1, 0],
        [1, 1, 1],
        [0, 1, 0],
    ]
    sample_x_filter = [
        [1, 0, 1],
        [0, 1, 0],
        [1, 0, 1],
    ]
    mac_performance_rows = [(
        3,
        measure_mac(sample_3x3, sample_3x3),
        None,
    )]
    classification_performance_rows = [(
        3,
        measure_classification(sample_3x3, sample_3x3, sample_x_filter),
        None,
    )]

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
            x_filter = normalized_filters["X"]
            validate_numeric_matrix(pattern, size, f"size_{size}_1 패턴")
            validate_numeric_matrix(cross_filter, size, f"size_{size} Cross 필터")
            validate_numeric_matrix(x_filter, size, f"size_{size} X 필터")
            mac_performance_rows.append(
                (size, measure_mac(pattern, cross_filter), None)
            )
            classification_performance_rows.append(
                (
                    size,
                    measure_classification(pattern, cross_filter, x_filter),
                    None,
                )
            )
        except ValueError as error:
            mac_performance_rows.append((size, None, str(error)))
            classification_performance_rows.append((size, None, str(error)))

    print("")
    print("성능 분석 (Cross MAC 10회 평균)")
    print_mac_performance_table(mac_performance_rows)

    print("")
    print("보충 성능 분석 (판정 10회, 크기별 MAC 호출 총 20회)")
    print_classification_performance_table(classification_performance_rows)

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


def main():
    """종료할 때까지 사용자 입력 모드와 JSON 분석 모드를 반복 실행"""
    print("=== Mini NPU Simulator ===")
    while True:
        print("")
        print("[모드 선택]")
        print("1. 사용자 입력 (3 x 3)")
        print("2. data.json 분석")
        print("0. 종료")
        choice = input("선택: ")

        if choice == "1":
            run_user_mode()
            continue
        if choice == "2":
            run_json_mode()
            continue
        if choice == "0":
            print("프로그램을 종료합니다.")
            return

        print("선택 오류: 0, 1 또는 2를 입력하세요.")


if __name__ == "__main__":
    main()
