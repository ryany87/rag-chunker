from rag_chunker.tokens import estimate_tokens, fits_budget


def test_empty_text_is_zero_tokens():
    assert estimate_tokens("") == 0


def test_short_word_is_one_token():
    assert estimate_tokens("hi") == 1


def test_word_scales_at_four_chars_per_token():
    assert estimate_tokens("hello") == 2


def test_short_digit_run_is_one_token():
    assert estimate_tokens("123") == 1


def test_digit_run_scales_at_three_chars_per_token():
    assert estimate_tokens("12345") == 2


def test_symbols_cost_more_than_letters():
    assert estimate_tokens("!!!") == 2


def test_newline_runs_are_cheap():
    assert estimate_tokens("a\nb") == 3


def test_cjk_is_one_token_per_character():
    assert estimate_tokens("中文") == 2


def test_fits_budget_matches_estimate():
    assert fits_budget("hello", 2) is True
    assert fits_budget("hello", 1) is False
