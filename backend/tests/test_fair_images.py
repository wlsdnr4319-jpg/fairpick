"""관리자 표지 이미지 업로드 (직접 찍었거나 허락받은 이미지만, 서버에서 검사·WebP 변환)."""

from io import BytesIO

import pytest
from PIL import Image

from app.core.config import get_settings
from app.services import images
from tests import factories as f

URL = "/api/v1/admin/fairs/{}/image"


@pytest.fixture(autouse=True)
def upload_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "upload_dir", str(tmp_path))
    return tmp_path / "fairs"


@pytest.fixture
def ctx(db):
    cat = f.category(db, "food", "식음료")
    ven = f.venue(db, name="코엑스")
    fair = f.fair(db, category=cat, venue=ven, title="커피 엑스포")
    return {"fair": fair, "h": f.auth_header(f.admin(db)), "user_h": f.auth_header(f.user(db))}


def png(size=(2400, 1200), color=(200, 120, 40), exif_gps=False) -> bytes:
    img = Image.new("RGB", size, color)
    out = BytesIO()
    if exif_gps:
        exif = Image.Exif()
        exif[0x8825] = {2: (37.0, 30.0, 0.0)}  # GPSInfo: 위도
        img.save(out, "JPEG", exif=exif)
    else:
        img.save(out, "PNG")
    return out.getvalue()


def upload(client, ctx, data, *, name="photo.png", rights=True, headers=None):
    return client.put(
        URL.format(ctx["fair"].id),
        files={"file": (name, data, "image/png")},
        data={"rights_confirmed": "true" if rights else "false"},
        headers=headers or ctx["h"],
    )


def test_upload_resizes_to_webp_and_serves_it(client, ctx, upload_dir):
    res = upload(client, ctx, png())
    assert res.status_code == 200, res.text
    url = res.json()["image_url"]
    assert url.startswith("/api/v1/uploads/fairs/") and url.endswith(".webp")

    # 공개 상세 API 도 같은 주소를 준다 (FairCover 가 이 주소로 그린다)
    assert client.get(f"/api/v1/fairs/{ctx['fair'].id}").json()["image_url"] == url

    got = client.get(url)
    assert got.status_code == 200
    assert got.headers["content-type"] == "image/webp"
    assert got.headers["x-content-type-options"] == "nosniff"
    assert "immutable" in got.headers["cache-control"]
    with Image.open(BytesIO(got.content)) as img:
        assert img.format == "WEBP"
        assert max(img.size) == 1600  # 긴 변 1600 으로 줄인다
    assert len(list(upload_dir.iterdir())) == 1


def test_exif_location_is_removed(client, ctx):
    res = upload(client, ctx, png(size=(800, 600), exif_gps=True), name="phone.jpg")
    assert res.status_code == 200, res.text
    with Image.open(BytesIO(client.get(res.json()["image_url"]).content)) as img:
        assert not img.getexif()  # 촬영 위치(GPS)가 남지 않는다


def test_replacing_or_deleting_removes_old_file(client, ctx, upload_dir):
    first = upload(client, ctx, png()).json()["image_url"]
    second = upload(client, ctx, png(color=(10, 10, 10))).json()["image_url"]
    assert first != second
    assert [p.name for p in upload_dir.iterdir()] == [second.rsplit("/", 1)[1]]
    assert client.get(first).status_code == 404

    res = client.delete(URL.format(ctx["fair"].id), headers=ctx["h"])
    assert res.status_code == 200 and res.json()["image_url"] is None
    assert list(upload_dir.iterdir()) == []


@pytest.mark.parametrize(
    ("data", "name"),
    [
        (b"<svg xmlns='http://www.w3.org/2000/svg' onload='alert(1)'/>", "x.png"),  # 이미지인 척하는 SVG
        (b"<html><script>alert(1)</script></html>", "x.jpg"),
        (png()[:200], "broken.png"),  # 잘린 파일
    ],
)
def test_rejects_non_images_by_content(client, ctx, upload_dir, data, name):
    res = upload(client, ctx, data, name=name)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "IMAGE_INVALID"
    assert not upload_dir.exists() or list(upload_dir.iterdir()) == []


def test_rejects_gif(client, ctx):
    out = BytesIO()
    Image.new("RGB", (10, 10)).save(out, "GIF")
    assert upload(client, ctx, out.getvalue()).json()["error"]["code"] == "IMAGE_INVALID"


def test_rejects_too_large_file(client, ctx, monkeypatch):
    monkeypatch.setattr(get_settings(), "upload_max_bytes", 1000)
    res = upload(client, ctx, png())
    assert res.status_code == 413
    assert res.json()["error"]["code"] == "IMAGE_TOO_LARGE"


def test_rejects_decompression_bomb(client, ctx, monkeypatch):
    monkeypatch.setattr(images, "MAX_PIXELS", 100)
    assert upload(client, ctx, png(size=(20, 20))).json()["error"]["code"] == "IMAGE_INVALID"


def test_requires_rights_confirmation(client, ctx):
    res = upload(client, ctx, png(), rights=False)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "RIGHTS_NOT_CONFIRMED"


def test_admin_only(client, ctx):
    assert upload(client, ctx, png(), headers=ctx["user_h"]).status_code == 403
    assert client.delete(URL.format(ctx["fair"].id), headers=ctx["user_h"]).status_code == 403


def test_unknown_fair_is_404(client, ctx):
    ctx = {**ctx, "fair": type("Missing", (), {"id": 999999})}
    assert upload(client, ctx, png()).status_code == 404


@pytest.mark.parametrize("name", ["..%2F..%2Fapp%2Fmain.py", "1-short.webp", "1-aaaaaaaaaaaaaaaa.png", "x.webp"])
def test_serving_only_accepts_server_made_names(client, name):
    assert client.get(f"/api/v1/uploads/fairs/{name}").status_code == 404
