from app.normalize import clean_text, content_hash, html_to_text, unique_nonempty


def test_html_to_text_keeps_paragraphs_and_bullets():
    html = (
        "<h2>About us</h2><p>We build&nbsp;AI &amp; tools.</p>"
        "<ul><li><p>Python</p></li><li>Postgres</li></ul>"
        "<script>track()</script>"
    )

    assert html_to_text(html) == "About us\n\nWe build AI & tools.\n\n- Python\n\n- Postgres"


def test_clean_text_collapses_spaces_and_blank_lines():
    assert clean_text("  Hello   world \r\n\r\n\r\n\r\nBye\t\tnow  ") == "Hello world\n\nBye now"


def test_content_hash_ignores_case_and_spacing():
    a = content_hash("Cohere", "ML Engineer", "Build  models.\n\nShip them.")
    b = content_hash("cohere", "ml engineer", "Build models. Ship them.")

    assert a == b


def test_content_hash_differs_for_different_jobs():
    assert content_hash("Cohere", "ML Engineer", "x") != content_hash("Cohere", "AI Engineer", "x")


def test_unique_nonempty_strips_and_drops_repeats():
    assert unique_nonempty([" London ", None, "", "Toronto", "London"]) == ["London", "Toronto"]
