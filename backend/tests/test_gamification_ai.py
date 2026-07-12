from types import SimpleNamespace

from app.config import Settings
from app.gamification_ai import _validated_suggestions, ai_challenges_available


def test_ai_challenges_require_an_openai_key():
    assert not ai_challenges_available(Settings(openai_api_key=None))
    assert ai_challenges_available(SimpleNamespace(openai_api_key="test-key"))


def test_ai_suggestions_are_allowlisted_and_safety_filtered():
    suggestions = _validated_suggestions(
        {
            "suggestions": [
                {
                    "template_key": "safe",
                    "title": "Ruhige Wochenrunde",
                    "description": "Eine kurze Runde bei sicheren Bedingungen.",
                    "metric": "activity_count",
                    "target_value": 2,
                    "duration_days": 7,
                    "reward_xp": 35,
                    "weather_sensitive": True,
                },
                {
                    "title": "Gewitter-Challenge",
                    "description": "Fahre trotz Gewitter weiter.",
                    "metric": "activity_count",
                    "target_value": 1,
                },
                {
                    "title": "Nicht erlaubte Metrik",
                    "description": "Darf nicht gespeichert werden.",
                    "metric": "social_rank",
                    "target_value": 1,
                },
            ]
        }
    )
    assert len(suggestions) == 1
    assert suggestions[0]["metric"] == "activity_count"
    assert suggestions[0]["safety_note"]
