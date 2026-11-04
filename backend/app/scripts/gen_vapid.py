"""
웹 푸시용 VAPID 키 쌍을 만든다. 실행: python -m app.scripts.gen_vapid
출력 두 줄을 .env 에 붙여 넣는다. 키를 바꾸면 기존 구독은 모두 다시 해야 하므로 한 번 만들면 유지한다.

- VAPID_PUBLIC_KEY: 브라우저가 구독할 때 쓰는 공개 키 (P-256 공개점 65바이트, base64url)
- VAPID_PRIVATE_KEY: 서버가 푸시 요청에 서명하는 비밀 키 (32바이트, base64url). 저장소에 올리지 않는다
"""

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def generate() -> tuple[str, str]:
    key = ec.generate_private_key(ec.SECP256R1())
    private = key.private_numbers().private_value.to_bytes(32, "big")
    public = key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return _b64(public), _b64(private)


if __name__ == "__main__":
    public, private = generate()
    print(f"VAPID_PUBLIC_KEY={public}")
    print(f"VAPID_PRIVATE_KEY={private}")
