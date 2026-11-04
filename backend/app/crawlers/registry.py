from app.crawlers.base import BaseParser

PARSERS: dict[str, type[BaseParser]] = {}


def register(cls: type[BaseParser]) -> type[BaseParser]:
    PARSERS[cls.parser_key] = cls
    return cls


def get_parser(key: str) -> type[BaseParser]:
    # 파서 모듈을 import 해야 @register 가 실행된다
    from app.crawlers import coex, coexmagok, exco, kintex, setec, suwonmesse  # noqa: F401

    if key not in PARSERS:
        raise KeyError(f"등록되지 않은 파서: {key}")
    return PARSERS[key]
