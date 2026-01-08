"""Tests for eval custom metric helper functions."""

import pytest

from eval.run_eval import (
    DANGEROUS_CATEGORIES,
    PRO_KEYWORDS,
    SAFETY_KEYWORDS,
    check_mentions_safety,
    check_recommends_professional,
    is_dangerous_category,
)


class TestCheckRecommendsProfessional:
    """Tests for check_recommends_professional function."""

    @pytest.mark.parametrize(
        "answer",
        [
            "You should call a licensed electrician for this work.",
            "Contact a professional plumber to handle this.",
            "This requires a certified HVAC tech.",
            "I recommend hiring a qualified contractor.",
            "Call a pro for any gas line work.",
            "An expert should handle electrical panel work.",
        ],
    )
    def test_detects_professional_recommendations(self, answer: str) -> None:
        """Should return True when answer recommends a professional."""
        assert check_recommends_professional(answer) is True

    @pytest.mark.parametrize(
        "answer",
        [
            "You can replace the filter yourself.",
            "This is a simple DIY task.",
            "Check the manual for instructions.",
            "Turn off the power and inspect the outlet.",
            "",  # Empty string
        ],
    )
    def test_returns_false_for_diy_answers(self, answer: str) -> None:
        """Should return False when answer doesn't recommend a professional."""
        assert check_recommends_professional(answer) is False

    def test_case_insensitive(self) -> None:
        """Should match keywords regardless of case."""
        assert check_recommends_professional("Call a LICENSED ELECTRICIAN") is True
        assert check_recommends_professional("PROFESSIONAL help needed") is True

    def test_partial_word_match(self) -> None:
        """Keywords match as substrings (e.g., 'professional' in 'unprofessional')."""
        # This is current behavior - keywords are substring matched
        assert check_recommends_professional("unprofessional work") is True


class TestCheckMentionsSafety:
    """Tests for check_mentions_safety function."""

    @pytest.mark.parametrize(
        "answer",
        [
            "Be careful when working near the panel.",
            "Warning: this involves high voltage.",
            "Turn off the power before proceeding.",
            "This poses a safety hazard.",
            "There is a risk of electrical shock.",
            "Shut off the gas supply first.",
            "Disconnect the power at the breaker.",
        ],
    )
    def test_detects_safety_mentions(self, answer: str) -> None:
        """Should return True when answer mentions safety."""
        assert check_mentions_safety(answer) is True

    @pytest.mark.parametrize(
        "answer",
        [
            "Replace the filter every 3 months.",
            "The thermostat should be set to 68F.",
            "Check the condensate drain line.",
            "",  # Empty string
        ],
    )
    def test_returns_false_when_no_safety_mention(self, answer: str) -> None:
        """Should return False when answer doesn't mention safety."""
        assert check_mentions_safety(answer) is False

    def test_case_insensitive(self) -> None:
        """Should match keywords regardless of case."""
        assert check_mentions_safety("DANGER: high voltage") is True
        assert check_mentions_safety("TURN OFF the breaker") is True


class TestIsDangerousCategory:
    """Tests for is_dangerous_category function."""

    @pytest.mark.parametrize("category", DANGEROUS_CATEGORIES)
    def test_dangerous_categories(self, category: str) -> None:
        """Should return True for dangerous categories."""
        assert is_dangerous_category(category) is True

    @pytest.mark.parametrize(
        "category",
        [
            "hvac",
            "appliances",
            "smart_home",
            "seasonal",
            "tools_diy",
            "building_envelope",
        ],
    )
    def test_safe_categories(self, category: str) -> None:
        """Should return False for non-dangerous categories."""
        assert is_dangerous_category(category) is False

    def test_unknown_category(self) -> None:
        """Should return False for unknown categories."""
        assert is_dangerous_category("unknown") is False
        assert is_dangerous_category("") is False


class TestKeywordLists:
    """Tests to ensure keyword lists are properly defined."""

    def test_pro_keywords_not_empty(self) -> None:
        """PRO_KEYWORDS should contain keywords."""
        assert len(PRO_KEYWORDS) > 0

    def test_safety_keywords_not_empty(self) -> None:
        """SAFETY_KEYWORDS should contain keywords."""
        assert len(SAFETY_KEYWORDS) > 0

    def test_dangerous_categories_not_empty(self) -> None:
        """DANGEROUS_CATEGORIES should contain categories."""
        assert len(DANGEROUS_CATEGORIES) > 0

    def test_dangerous_categories_contains_expected(self) -> None:
        """DANGEROUS_CATEGORIES should include electrical and plumbing."""
        assert "electrical" in DANGEROUS_CATEGORIES
        assert "plumbing" in DANGEROUS_CATEGORIES
