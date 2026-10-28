from scripts.verify_oracle_deployment import check


def test_check_accepts_expected_status(monkeypatch) -> None:
    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(
        "scripts.verify_oracle_deployment.urlopen", lambda *_args, **_kwargs: Response()
    )
    assert check("https://example.test/health", {200}) == (True, "https://example.test/health: 200")


def test_check_rejects_unexpected_status(monkeypatch) -> None:
    class Response:
        status = 503

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(
        "scripts.verify_oracle_deployment.urlopen", lambda *_args, **_kwargs: Response()
    )
    passed, message = check("https://example.test/health", {200})
    assert not passed
    assert "503" in message
