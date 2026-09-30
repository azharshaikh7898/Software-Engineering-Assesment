from app.qa import parse_answer


def test_fullwidth_brackets_and_narrow_space_are_normalised():
    # real reply from the model during manual testing
    answer, cited = parse_answer("150\u202fUSD per night\u30101\u3011", 2)
    assert answer == "150 USD per night[1]" and cited == [1]


def test_ascii_and_fullwidth_fullstop_variants():
    assert parse_answer("See \uff3b2\uff3d.", 2) == ("See [2].", [2])
    assert parse_answer("Both apply [1, 2].", 2)[1] == [1, 2]


def test_uncited_or_out_of_range_answers_are_still_refused():
    assert parse_answer("150 USD per night", 2) == (None, [])
    assert parse_answer("150 USD per night\u30109\u3011", 2) == (None, [])
    assert parse_answer("NOT_FOUND", 2) == (None, [])
