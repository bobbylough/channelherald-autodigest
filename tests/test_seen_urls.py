from digest.seen_urls import SeenUrls


def test_contains_returns_false_for_fresh_db(tmp_path):
    db = SeenUrls(str(tmp_path / "seen.db"))
    assert db.contains("https://example.com/a") is False


def test_contains_returns_true_after_add(tmp_path):
    db = SeenUrls(str(tmp_path / "seen.db"))
    db.add("https://example.com/a")
    assert db.contains("https://example.com/a") is True


def test_second_instance_sees_added_url(tmp_path):
    path = str(tmp_path / "seen.db")
    db1 = SeenUrls(path)
    db1.add("https://example.com/persistent")
    db2 = SeenUrls(path)
    assert db2.contains("https://example.com/persistent") is True


def test_contains_returns_false_for_different_url(tmp_path):
    db = SeenUrls(str(tmp_path / "seen.db"))
    db.add("https://example.com/a")
    assert db.contains("https://example.com/b") is False
