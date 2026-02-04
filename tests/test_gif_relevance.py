from utils.gif_reply import _is_relevant_to_text


def test_relevant_overlap():
    assert _is_relevant_to_text("happy birthday", "Happy birthday to you!") is True


def test_irrelevant_query():
    assert _is_relevant_to_text("cat", "Please update the config settings") is False


def test_reaction_keyword_with_emotion_cue():
    assert _is_relevant_to_text("laughing", "lol that's great") is True


def test_stopword_only_query():
    assert _is_relevant_to_text("the", "the quick brown fox") is False


def test_reaction_phrase_with_emotion_cue():
    assert _is_relevant_to_text("thumbs up", "nice work on the deploy") is True
