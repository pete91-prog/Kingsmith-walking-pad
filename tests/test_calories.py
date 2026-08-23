from kingsmith_walkingpad.calories import SessionCalories, walking_kcal


def test_zero_inputs() -> None:
    assert walking_kcal(0, 60) == 0
    assert walking_kcal(3, 0) == 0


def test_known_acsm_point() -> None:
    # 3 km/h for 60 s at 75 kg
    # speed = 50 m/min, VO2 = 8.5, kcal/min = 3.1875, 1 min → 3.1875
    assert round(walking_kcal(3.0, 60, 75), 3) == 3.188


def test_session_integrates_speed_changes() -> None:
    session = SessionCalories(75)
    session.update(3.0, 0)
    session.update(3.0, 60)
    first = session.total
    session.update(0.0, 120)
    # second minute was at 3 km/h (previous speed)
    assert session.total == first * 2
    session.update(0.0, 180)
    assert session.total == first * 2
