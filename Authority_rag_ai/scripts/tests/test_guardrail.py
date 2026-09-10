from app.services.guardrail_service import GuardrailService


def test_guardrail_clean_input():
    guardrail = GuardrailService()
    result = guardrail.validate_input("What is the PMS document system?")
    assert result.is_safe is True
    assert result.reason is None


def test_guardrail_profane_input():
    guardrail = GuardrailService()
    result = guardrail.validate_input("This is fucking bullshit!")
    assert result.is_safe is False
    assert result.reason is not None
    assert "****" in result.censored_text


def test_guardrail_obfuscated_input():
    guardrail = GuardrailService()
    result = guardrail.validate_input("what the f*ck is this sh1t")
    assert result.is_safe is False


if __name__ == "__main__":
    test_guardrail_clean_input()
    test_guardrail_profane_input()
    test_guardrail_obfuscated_input()
    print("All guardrail tests passed successfully!")
