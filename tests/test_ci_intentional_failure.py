"""Temporary controlled failure proving that CI blocks a failing fast test."""


def test_ci_intentional_failure():
    assert False, "Controlled GRANT-02 CI failure evidence"
