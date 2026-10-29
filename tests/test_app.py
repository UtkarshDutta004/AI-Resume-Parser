import io

from app import create_app


def test_parse_endpoint_returns_candidate_json():
    client = create_app({"TESTING": True}).test_client()
    response = client.post(
        "/api/parse",
        data={"file": (io.BytesIO(
            b"Taylor Reed\ntaylor@example.com\n+1 415 555 0132\n\nSKILLS\nPython, JavaScript"
        ), "../../resume.txt")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["candidate"]["name"] == "Taylor Reed"
    assert body["candidate"]["email"] == "taylor@example.com"
    assert body["candidate"]["skills"] == ["JavaScript", "Python"]
    assert body["filename"] == "resume.txt"


def test_homepage_renders_upload_interface():
    response = create_app({"TESTING": True}).test_client().get("/")
    assert response.status_code == 200
    assert b"Drop your resume here" in response.data


def test_parse_endpoint_rejects_missing_and_unsupported_files():
    client = create_app({"TESTING": True}).test_client()
    missing = client.post("/api/parse", data={}, content_type="multipart/form-data")
    unsupported = client.post(
        "/api/parse",
        data={"file": (io.BytesIO(b"data"), "resume.exe")},
        content_type="multipart/form-data",
    )
    assert missing.status_code == 400
    assert unsupported.status_code == 415


def test_parse_endpoint_rejects_empty_and_unreadable_files():
    client = create_app({"TESTING": True}).test_client()
    empty = client.post(
        "/api/parse",
        data={"file": (io.BytesIO(b""), "empty.txt")},
        content_type="multipart/form-data",
    )
    unreadable = client.post(
        "/api/parse",
        data={"file": (io.BytesIO(b"not a PDF"), "broken.pdf")},
        content_type="multipart/form-data",
    )
    assert empty.status_code == 400
    assert unreadable.status_code == 422


def test_parse_endpoint_enforces_configured_size_limit():
    client = create_app({
        "TESTING": True,
        "MAX_UPLOAD_SIZE": 32,
        "MAX_CONTENT_LENGTH": 4096,
    }).test_client()
    response = client.post(
        "/api/parse",
        data={"file": (io.BytesIO(b"x" * 100), "resume.txt")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 413
