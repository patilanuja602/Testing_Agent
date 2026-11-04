"""Single threshold, fixed comparison: complexity >= threshold -> Exceeds Threshold."""
import pytest

import config
import models.analysis_result as models
from core.threshold_manager import apply_threshold, classify, count_by_status, exceeds
from models.analysis_result import AnalysisStatus, ThresholdConfig, ThresholdStatus
from tests.helpers import fn

OK = AnalysisStatus.SUCCESS


def cfg(value=10):
    return ThresholdConfig(value)


# ------------------------------------------------------------------ boundary behaviour
@pytest.mark.parametrize("ccn,expected", [(3, False), (4, False), (5, True), (6, True), (8, True)])
def test_specification_example_threshold_5(ccn, expected):
    assert exceeds(ccn, cfg(5)) is expected
    status = ThresholdStatus.EXCEEDS if expected else ThresholdStatus.WITHIN
    assert classify(ccn, OK, cfg(5)) is status


@pytest.mark.parametrize("threshold", [1, 2, 5, 10, 11, 50, 1000])
def test_value_equal_to_threshold_is_flagged(threshold):
    assert exceeds(threshold, cfg(threshold)) is True
    assert exceeds(threshold - 1, cfg(threshold)) is False       # one below is within
    assert exceeds(threshold + 1, cfg(threshold)) is True        # one above is flagged


def test_default_threshold_is_one_and_flags_every_function():
    assert config.DEFAULT_THRESHOLD == 1 and config.MIN_THRESHOLD == 1
    # a function cannot have complexity below 1, so with the default every function is flagged
    assert all(exceeds(c, cfg(config.DEFAULT_THRESHOLD)) for c in (1, 2, 10))


# ------------------------------------------------------------------ one threshold, no modes
def test_removed_threshold_modes_no_longer_exist():
    assert not hasattr(models, "ComparisonMode") and not hasattr(models, "ThresholdSource")
    assert [f for f in ThresholdConfig.__dataclass_fields__] == ["value"]


@pytest.mark.parametrize("bad", [0, -1, -10, 1.5, "5", None, True])
def test_threshold_must_be_a_positive_integer(bad):
    with pytest.raises(ValueError):
        ThresholdConfig(bad)


def test_rule_text_states_the_fixed_rule():
    assert cfg(7).rule_text() == "Exceeds Threshold when complexity >= 7"


# ------------------------------------------------------------------ classification
def test_missing_values_are_never_classified_as_within():
    assert classify(None, OK, cfg(5)) is ThresholdStatus.NOT_ANALYZED
    assert classify(None, AnalysisStatus.FAILED, cfg(5)) is ThresholdStatus.NOT_ANALYZED
    assert classify(None, AnalysisStatus.WARNING, cfg(5)) is ThresholdStatus.WARNING


def test_warning_status_does_not_change_score_classification():
    assert classify(12, AnalysisStatus.WARNING, cfg(10)) is ThresholdStatus.EXCEEDS
    assert classify(4, AnalysisStatus.WARNING, cfg(5)) is ThresholdStatus.WITHIN


def test_apply_does_not_mutate_and_reclassifies_on_threshold_change():
    originals = [fn("a", 10), fn("b", 9), fn("c", None)]
    at10 = apply_threshold(originals, cfg(10))
    at9 = apply_threshold(originals, cfg(9))
    assert [r.threshold_status for r in at10] == [ThresholdStatus.EXCEEDS, ThresholdStatus.WITHIN, ThresholdStatus.NOT_ANALYZED]
    assert [r.threshold_status for r in at9] == [ThresholdStatus.EXCEEDS, ThresholdStatus.EXCEEDS, ThresholdStatus.NOT_ANALYZED]
    assert all(r.threshold_status is ThresholdStatus.NOT_ANALYZED for r in originals)
    counts = count_by_status(at10)
    assert counts[ThresholdStatus.EXCEEDS] == 1 and counts[ThresholdStatus.WITHIN] == 1
