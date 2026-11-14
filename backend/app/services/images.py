"""
박람회 표지 이미지 업로드 (관리자 전용).

공식 포스터는 저작권 때문에 가져오지 않는다(11-14 결정). 관리자가 직접 찍었거나 사용 허락을 받은
이미지만 올리고, 없으면 화면이 주제 예시 사진(Pexels)이나 일러스트 표지(FairCover)를 쓴다.

올린 파일은 그대로 저장하지 않는다:
- 확장자·Content-Type 은 믿지 않고 Pillow 로 실제 내용을 열어 JPEG·PNG·WebP 만 받는다
  (이미지인 척하는 HTML·SVG 를 같은 도메인에서 내려주면 XSS 가 된다)
- 너무 큰 해상도(압축 폭탄)는 열기 전에 거절한다
- 긴 변 1600px 로 줄이고 WebP 로 다시 저장한다. 이때 EXIF(촬영 위치 GPS 등)가 빠진다
- 파일 이름은 서버가 정한다: {박람회 id}-{무작위}.webp (사용자가 준 이름은 쓰지 않아 경로 조작이 불가능)
"""

import logging
import re
import secrets
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.models import Fair

logger = logging.getLogger(__name__)

URL_PREFIX = "/api/v1/uploads/fairs/"
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_PIXELS = 40_000_000  # 약 8000x5000. 이보다 크면 압축 폭탄일 수 있어 디코딩하지 않는다
MAX_SIDE = 1600
NAME_RE = re.compile(r"^\d+-[A-Za-z0-9_-]{16,}\.webp$")


def upload_root() -> Path:
    return Path(get_settings().upload_dir) / "fairs"


def _file_of(image_url: str | None) -> Path | None:
    """우리가 저장한 이미지 주소면 디스크 경로를, 외부 주소면 None 을 돌려준다."""
    if not image_url or not image_url.startswith(URL_PREFIX):
        return None
    name = image_url.removeprefix(URL_PREFIX)
    return upload_root() / name if NAME_RE.match(name) else None


def to_webp(data: bytes) -> bytes:
    if len(data) > get_settings().upload_max_bytes:
        raise AppError(413, "IMAGE_TOO_LARGE", "이미지는 5MB 이하만 올릴 수 있어요")
    try:
        with Image.open(BytesIO(data)) as probe:
            if probe.format not in ALLOWED_FORMATS:
                raise AppError(422, "IMAGE_INVALID", "JPG·PNG·WebP 이미지만 올릴 수 있어요")
            if probe.width * probe.height > MAX_PIXELS:
                raise AppError(422, "IMAGE_INVALID", "해상도가 너무 커요. 8000×5000 이하로 줄여 주세요")
            probe.verify()  # 잘린 파일·깨진 파일 거르기 (verify 뒤에는 다시 열어야 한다)
        with Image.open(BytesIO(data)) as img:
            img = ImageOps.exif_transpose(img)  # 휴대폰 사진의 회전 정보를 픽셀에 반영한 뒤 EXIF 는 버린다
            img.thumbnail((MAX_SIDE, MAX_SIDE))
            img = img.convert("RGBA" if img.mode in ("RGBA", "LA", "P") else "RGB")
            out = BytesIO()
            img.save(out, "WEBP", quality=82, method=4)
            return out.getvalue()
    except AppError:
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError) as e:
        raise AppError(422, "IMAGE_INVALID", "이미지 파일을 읽을 수 없어요") from e


def remove_file(image_url: str | None) -> None:
    """DB 커밋이 끝난 뒤에 부른다. 커밋 전에 지웠다가 롤백되면 DB 가 없는 파일을 가리킨다."""
    path = _file_of(image_url)
    if path is not None:
        try:
            path.unlink(missing_ok=True)
        except OSError:  # 지우지 못해도 DB 는 이미 새 값이다. 남은 파일은 로그로 찾는다
            logger.warning("old image not removed: %s", path)


def set_image(db: Session, fair: Fair, data: bytes) -> str | None:
    """새 이미지를 저장하고 바꾼다. 지워야 할 이전 이미지 주소를 돌려준다 (커밋 뒤 remove_file)."""
    webp = to_webp(data)
    root = upload_root()
    root.mkdir(parents=True, exist_ok=True)
    name = f"{fair.id}-{secrets.token_urlsafe(12)}.webp"
    (root / name).write_bytes(webp)
    old = fair.image_url
    fair.image_url = URL_PREFIX + name
    db.flush()
    return old


def clear_image(db: Session, fair: Fair) -> str | None:
    old = fair.image_url
    fair.image_url = None
    db.flush()
    return old


def file_for(name: str) -> Path | None:
    """GET /uploads/fairs/{name}: 서버가 만든 이름 형식이 아니면 디스크를 보지도 않는다."""
    if not NAME_RE.match(name):
        return None
    path = upload_root() / name
    return path if path.is_file() else None
