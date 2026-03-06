from functools import lru_cache
from pathlib import Path
import re
import unicodedata
from typing import Any, Callable

# 公共敏感词过滤模块：统一词库加载、命中检测和错误返回构建
_SHORT_ASCII_RE = re.compile(r"^[a-z0-9]{1,2}$", re.IGNORECASE)
_ONLY_SYMBOL_RE = re.compile(r"^[\W_]+$", re.UNICODE)
_INDEXED_ENTRY_RE = re.compile(r"^\d+[.:\u3001\uff1a].*")
_IP_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}(?::\d{1,5})?$")
_DOMAIN_RE = re.compile(r"^(?:[a-z0-9-]+\.)+[a-z]{2,}(?::\d{1,5})?$", re.IGNORECASE)


def _candidate_sensitive_lexicon_dirs() -> list[Path]:
    this_file = Path(__file__).resolve()
    return [
        this_file.parent.parent / "third_party" / "Sensitive-lexicon" / "Vocabulary",
        this_file.parent / "third_party" / "Sensitive-lexicon" / "Vocabulary",
    ]


def _read_text_with_fallback_encodings(path: Path):
    for enc in ("utf-8", "utf-8-sig", "gb18030", "gbk"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
        except Exception:
            return None
    return None


def _normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value or "").strip().lower()


def _is_noisy_word(word: str) -> bool:
    if not word:
        return True
    if len(word) == 1:
        return True
    if word.isdigit():
        return True
    if len(word) > 64:
        return True
    if _ONLY_SYMBOL_RE.fullmatch(word):
        return True
    if _SHORT_ASCII_RE.fullmatch(word):
        return True
    if _INDEXED_ENTRY_RE.fullmatch(word):
        return True
    if _IP_RE.fullmatch(word):
        return True
    if _DOMAIN_RE.fullmatch(word):
        return True
    if word.startswith(("http://", "https://", "www.")):
        return True
    return False


def _is_ascii_word_char(ch: str) -> bool:
    return ch.isascii() and (ch.isalnum() or ch == "_")


def _contains_ascii_token(text: str, token: str) -> bool:
    start = 0
    token_len = len(token)
    text_len = len(text)
    while True:
        idx = text.find(token, start)
        if idx < 0:
            return False
        left_ok = idx == 0 or not _is_ascii_word_char(text[idx - 1])
        right_idx = idx + token_len
        right_ok = right_idx == text_len or not _is_ascii_word_char(text[right_idx])
        if left_ok and right_ok:
            return True
        start = idx + 1


@lru_cache(maxsize=1)
def load_sensitive_words() -> tuple[str, ...]:
    # 进程级缓存：词库只在首次调用时扫描一次，后续直接复用内存结果
    words: set[str] = set()

    for base_dir in _candidate_sensitive_lexicon_dirs():
        if not base_dir.exists() or not base_dir.is_dir():
            continue
        for txt_file in base_dir.rglob("*.txt"):
            text = _read_text_with_fallback_encodings(txt_file)
            if not text:
                continue
            for raw in text.splitlines():
                word = _normalize(raw.lstrip("\ufeff"))
                if not word or word.startswith("#") or _is_noisy_word(word):
                    continue
                words.add(word)

    return tuple(sorted(words, key=len, reverse=True))


def find_sensitive_word(text: str, scene: str = "username"):
    _ = scene
    lowered = _normalize(text)
    if not lowered:
        return None

    for word in load_sensitive_words():
        if not word:
            continue
        # 英文词按完整 token 匹配，避免把单词片段误判为敏感词
        if word.isascii() and word.isalnum():
            if _contains_ascii_token(lowered, word):
                return word
            continue
        if word in lowered:
            return word
    return None


def contains_sensitive_word(text: str, scene: str = "username") -> bool:
    return find_sensitive_word(text, scene=scene) is not None


def find_sensitive_in_fields(fields: dict[str, str], scene: str = "content"):
    for field_name, text in fields.items():
        value = (text or "").strip()
        if not value:
            continue
        hit = find_sensitive_word(value, scene=scene)
        if hit:
            return field_name, hit
    return None


def reject_sensitive_fields(
    fields: dict[str, str],
    err_builder: Callable[..., Any],
    scene: str = "content",
):
    # 路由层复用入口：命中即返回统一 400 文案，未命中返回 None
    hit = find_sensitive_in_fields(fields, scene=scene)
    if not hit:
        return None
    field_name, word = hit
    return err_builder(f"{field_name}包含敏感词汇：{word}", status=400)
