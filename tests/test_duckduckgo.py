from app.search.duckduckgo import _decode_ddg_url


def test_decode_ddg_redirect_url() -> None:
    href = "//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fdocs%3Fa%3D1"

    assert _decode_ddg_url(href) == "https://example.com/docs?a=1"

