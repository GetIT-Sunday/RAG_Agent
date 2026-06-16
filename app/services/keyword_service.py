import math
import re
from collections import Counter
from typing import Dict, Iterable, List

try:
    import jieba
except Exception:  # pragma: no cover - exercised only when dependency is missing
    jieba = None


STOPWORDS = {"的", "了", "和", "是", "我", "你", "他", "她", "它", "在", "有", "也", "就", "都", "而", "及", "与", "一个"}
SYNONYMS = {
    "小孩子": ["孩子", "少年", "儿童", "童年", "小时候", "小英雄", "闰土"],
    "孩子": ["小孩子", "少年", "儿童", "童年", "小时候"],
    "儿童": ["孩子", "小孩子", "少年", "童年"],
    "春天": ["春", "东风", "花", "草", "新绿", "春风"],
    "春": ["春天", "东风", "花", "草"],
    "少年闰土": ["闰土", "少年", "瓜地", "银圈", "猹"],
    "闰土": ["少年闰土", "少年", "瓜地", "银圈", "猹"],
    "百草园": ["百草園", "三味书屋", "三味書屋", "童年", "菜畦", "覆盆子", "何首乌", "何首烏"],
    "百草園": ["百草园", "三味书屋", "三味書屋", "童年", "菜畦", "覆盆子", "何首乌", "何首烏"],
    "三味书屋": ["三味書屋", "百草园", "百草園", "书塾", "書塾"],
    "三味書屋": ["三味书屋", "百草园", "百草園", "书塾", "書塾"],
    "童年趣事": ["童年", "少年", "孩子", "百草园", "百草園", "社戏", "社戲"],
    "看社戏": ["社戏", "社戲", "平桥村", "平橋村", "小伙伴", "少年"],
    "社戏": ["社戲", "平桥村", "平橋村", "小伙伴", "看戏", "看戲"],
    "社戲": ["社戏", "平桥村", "平橋村", "小伙伴", "看戏", "看戲"],
}


def tokenize_text(text: str) -> List[str]:
    text = text.strip()
    if not text:
        return []
    if jieba is not None:
        tokens = [t.strip() for t in jieba.lcut(text) if t.strip()]
    else:
        tokens = re.findall(r"[\u4e00-\u9fff]{1,4}|[A-Za-z0-9]+", text)
    output: List[str] = []
    for token in tokens:
        if token in STOPWORDS:
            continue
        if len(token) == 1 and not re.match(r"[\u4e00-\u9fff]", token):
            continue
        output.append(token)
    return output


def expand_query_terms(text: str) -> List[str]:
    terms: List[str] = []
    for key, values in SYNONYMS.items():
        if key in text:
            terms.extend(values)
    for token in tokenize_text(text):
        terms.extend(SYNONYMS.get(token, []))
    return terms


class KeywordService:
    def score(self, query: str, documents: Dict[int, str]) -> Dict[int, float]:
        if not query or not documents:
            return {doc_id: 0.0 for doc_id in documents}

        tokenized_docs = {doc_id: tokenize_text(text) for doc_id, text in documents.items()}
        query_tokens = tokenize_text(query) + expand_query_terms(query)
        if not query_tokens:
            return {doc_id: 0.0 for doc_id in documents}

        doc_count = len(documents)
        df: Counter[str] = Counter()
        for tokens in tokenized_docs.values():
            for token in set(tokens):
                df[token] += 1

        avg_len = sum(len(tokens) for tokens in tokenized_docs.values()) / max(doc_count, 1)
        raw_scores: Dict[int, float] = {}
        k1 = 1.5
        b = 0.75
        query_counter = Counter(query_tokens)

        for doc_id, tokens in tokenized_docs.items():
            tf = Counter(tokens)
            doc_len = len(tokens) or 1
            score = 0.0
            for token, qf in query_counter.items():
                if tf[token] == 0:
                    continue
                idf = math.log(1 + (doc_count - df[token] + 0.5) / (df[token] + 0.5))
                denom = tf[token] + k1 * (1 - b + b * doc_len / max(avg_len, 1))
                score += idf * ((tf[token] * (k1 + 1)) / denom) * qf
            raw_scores[doc_id] = score

        max_score = max(raw_scores.values(), default=0.0)
        if max_score <= 0:
            return {doc_id: 0.0 for doc_id in documents}
        return {doc_id: score / max_score for doc_id, score in raw_scores.items()}
