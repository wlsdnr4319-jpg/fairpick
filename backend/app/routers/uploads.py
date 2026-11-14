"""
관리자가 올린 표지 이미지 내려주기.

GET /api/v1/uploads/fairs/{name}

/api 아래에 두어 Vite 프록시·Nginx 의 /api/ 설정을 그대로 쓴다 (따로 정적 폴더를 열지 않음).
파일 이름에 무작위 값이 들어 있어 내용이 바뀌면 주소도 바뀌므로 오래 캐시해도 된다.
"""

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.core.errors import AppError
from app.services import images

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.get("/fairs/{name}", include_in_schema=False)
def fair_image(name: str):
    path = images.file_for(name)
    if path is None:
        raise AppError(404, "NOT_FOUND", "이미지를 찾을 수 없어요")
    return FileResponse(
        path,
        media_type="image/webp",  # 저장할 때 항상 WebP 로 다시 만든다
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "X-Content-Type-Options": "nosniff",
        },
    )
