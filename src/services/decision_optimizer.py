from datetime import datetime, timedelta
from typing import Dict
from dataclasses import dataclass

from src.ml.postprocess import enforce_monotonic_quantiles, compute_reliability_grade


@dataclass
class DecisionResult:
    recommended_leave_by: datetime
    scheduled_departure: datetime
    risk_delay_sec: float
    reliability_grade: str
    interquantile_spread: float
    guard_triggered: bool
    monotonic_quantiles: Dict[str, float]


def optimize_commute_decision(
    target_arrival: datetime, 
    scheduled_travel_sec: int, 
    raw_q10: float, 
    raw_q50: float, 
    raw_q90: float, 
    alpha: float
) -> DecisionResult:
    """
    Optimizes the commute decision based on scheduled travel times, historical ML quantiles,
    and the user's risk tolerance (alpha).
    """
    # 1. Enforce monotonic quantiles
    q10, q50, q90 = enforce_monotonic_quantiles(raw_q10, raw_q50, raw_q90)
    
    # 2. Select risk delay based on alpha tolerance
    # In RouteTrust, a lower alpha means less tolerance for being late.
    if alpha == 0.20:
        risk_delay_sec = q50
    elif alpha == 0.10:
        risk_delay_sec = q90
    elif alpha == 0.05:
        risk_delay_sec = q90 * 1.25
    else:
        # Fallback to median expectation if unsupported alpha is passed
        risk_delay_sec = q50

    # 3. Calculate theoretical departure times
    scheduled_departure = target_arrival - timedelta(seconds=scheduled_travel_sec)
    raw_leave_by = target_arrival - timedelta(seconds=(scheduled_travel_sec + risk_delay_sec))
    
    # 4. Early Departure Guard
    # If the model predicts an arrival earlier than scheduled (negative delay / early arrival),
    # clamp the recommendation to the scheduled departure. We cannot trust a bus to leave early.
    if raw_leave_by > scheduled_departure:
        recommended_leave_by = scheduled_departure
        guard_triggered = True
    else:
        recommended_leave_by = raw_leave_by
        guard_triggered = False
        
    # 5. Compute reliability grade
    grade, spread = compute_reliability_grade(q10, q50, q90)
    
    return DecisionResult(
        recommended_leave_by=recommended_leave_by,
        scheduled_departure=scheduled_departure,
        risk_delay_sec=float(risk_delay_sec),
        reliability_grade=grade,
        interquantile_spread=spread,
        guard_triggered=guard_triggered,
        monotonic_quantiles={"q10": q10, "q50": q50, "q90": q90}
    )
