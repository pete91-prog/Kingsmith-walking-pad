"""ACSM-level walking calorie estimate for pads that do not report energy."""

from __future__ import annotations

from .const import DEFAULT_WEIGHT_KG


def walking_kcal(speed_kmh: float, duration_s: float, weight_kg: float = DEFAULT_WEIGHT_KG) -> float:
    """Estimate kcal from constant-speed walking on a level grade.

    VO2 (ml/kg/min) = 0.1 * speed(m/min) + 3.5
    kcal/min        = VO2 * weight_kg / 200
    """
    if duration_s <= 0 or speed_kmh <= 0 or weight_kg <= 0:
        return 0.0
    speed_m_min = speed_kmh * 1000.0 / 60.0
    vo2 = 0.1 * speed_m_min + 3.5
    kcal_per_min = vo2 * weight_kg / 200.0
    return kcal_per_min * (duration_s / 60.0)


class SessionCalories:
    """Integrate ACSM calories across changing speeds."""

    def __init__(self, weight_kg: float = DEFAULT_WEIGHT_KG) -> None:
        self.weight_kg = weight_kg
        self.total = 0.0
        self._last_speed = 0.0
        self._last_elapsed: int | None = None

    def reset(self) -> None:
        self.total = 0.0
        self._last_speed = 0.0
        self._last_elapsed = None

    def update(self, speed_kmh: float, elapsed_s: int) -> float:
        if self._last_elapsed is None:
            self._last_elapsed = elapsed_s
            self._last_speed = speed_kmh
            return self.total
        delta = elapsed_s - self._last_elapsed
        if delta < 0:
            self.reset()
            self._last_elapsed = elapsed_s
            self._last_speed = speed_kmh
            return self.total
        if delta > 0:
            self.total += walking_kcal(self._last_speed, delta, self.weight_kg)
        self._last_elapsed = elapsed_s
        self._last_speed = speed_kmh
        return self.total
