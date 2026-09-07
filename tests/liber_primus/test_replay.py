from cicada.liber_primus.fixtures import load_fixtures, replay_all


def test_fixtures_exist():
    fixes = load_fixtures()
    assert fixes, "replay_fixtures.json must be generated before this test"


def test_known_pages_replay():
    rows = replay_all()
    failed = [r for r in rows if not r["ok"]]
    assert not failed, failed
