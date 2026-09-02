from app.services.image_format import detect_image_type


def test_detect_supported_image_types():
    assert detect_image_type(b"\xff\xd8\xffx") == "image/jpeg"
    assert detect_image_type(b"\x89PNG\r\n\x1a\nx") == "image/png"
    assert detect_image_type(b"GIF89ax") == "image/gif"
    assert detect_image_type(b"RIFFxxxxWEBP") == "image/webp"
    assert detect_image_type(b"not an image") is None
