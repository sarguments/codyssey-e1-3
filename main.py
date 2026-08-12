
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


def analyze_case(pattern_key, case_data, filters):
    """JSON 패턴 케이스 하나를 분석한 결과를 반환"""
    # 1. 패턴 키에서 크기 N 을 구한다.
    N = extract_pattern_size(pattern_key)

    # 2. `size_{N}` 키로 같은 크기의 필터 묶음을 가져온다.
    use_filtrs = filters[f"size_{N}"]

    # 3. 케이스의 `input`과 필터 두 개가 모두 올바른 정사각형인지 확인한다.
    if not is_square_matrix(case_data["input"], N):
        raise ValueError("패턴 크기가 올바르지 않습니다")

    if not is_square_matrix(use_filtrs["cross"], N):
        raise ValueError("Cross 필터 크기가 올바르지 않습니다")

    if not is_square_matrix(use_filtrs["x"], N):
        raise ValueError("X 필터 크기가 올바르지 않습니다")
    
    # 4. Cross 점수와 X 점수를 구한다.
    cross_score = mac(case_data['input'], use_filtrs['cross'])
    x_score = mac(case_data['input'], use_filtrs['x'])

    # 5. `compare_scores()` 결과 A/B를 Cross/X로 바꾼다. 동점은 UNDECIDED를 유지한다.
    prediction = 'UNDECIDED'
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
    return {
        "pattern_key": pattern_key,
        "size": N,
        "cross_score": cross_score,
        "x_score": x_score,
        "prediction": prediction,
        "expected": expected,
        "status": final_result,
    }

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
        except (ValueError, KeyError, TypeError) as error:
            # 알려진 에러인 경우 FAIL 처리, 에러 텍스트 포함
            results.append({
                    'pattern_key': k,
                    'status': 'FAIL',
                    'error': str(error)
                })
            failed += 1

    # 종합 결과 리턴
    return {
        "total": len(patterns),
        "passed": passed,
        "failed": failed,
        "results": results,
    }
