from app.services.keyword_service import KeywordService


def test_keyword_service_matches_runtu():
    docs = {
        1: "东风来了，春天的脚步近了，小草绿了。",
        2: "一个十一二岁的少年，项带银圈，他就是少年闰土。",
    }
    scores = KeywordService().score("少年闰土", docs)
    assert scores[2] > scores[1]
