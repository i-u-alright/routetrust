def enforce_monotonic_quantiles(q10: float, q50: float, q90: float) -> tuple[float, float, float]:
    """
    Ensures that the quantiles are strictly non-decreasing.
    Returns a sorted tuple such that q10_adj <= q50_adj <= q90_adj under all inputs.
    """
    sorted_q = sorted([q10, q50, q90])
    return (sorted_q[0], sorted_q[1], sorted_q[2])


def compute_reliability_grade(q10: float, q50: float, q90: float) -> tuple[str, float]:
    """
    Computes a reliability grade based on the relative width of the prediction interval.
    
    Spread = (q90 - q10) / max(q50, 60.0)
    
    Buckets:
    - Spread <= 0.15: 'A'
    - 0.15 < Spread <= 0.30: 'B'
    - 0.30 < Spread <= 0.50: 'C'
    - 0.50 < Spread <= 0.75: 'D'
    - Spread > 0.75: 'F'
    """
    # Enforce monotonic quantiles before computing spread to ensure positive spread
    q10, q50, q90 = enforce_monotonic_quantiles(q10, q50, q90)
    
    spread = (q90 - q10) / max(q50, 60.0)
    
    if spread <= 0.15:
        grade = 'A'
    elif spread <= 0.30:
        grade = 'B'
    elif spread <= 0.50:
        grade = 'C'
    elif spread <= 0.75:
        grade = 'D'
    else:
        grade = 'F'
        
    return grade, round(spread, 3)
