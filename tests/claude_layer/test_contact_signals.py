"""Unit tests for .claude/skills/researching-companies/scripts/contact_signals.py.
The enrich module is replaced by a fake, so no network call is made. Names are invented."""
import importlib.util
import pathlib

SCRIPT = pathlib.Path(__file__).resolve().parents[2] / ".claude/skills/researching-companies/scripts/contact_signals.py"
spec = importlib.util.spec_from_file_location("contact_signals", SCRIPT)
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)


class FakeEnrich:
    """stands in for enrich.py with fixed answers."""

    def __init__(self, org=None, members=(), mx=False, boom=None):
        self.org, self.members, self.mx, self.boom = org, list(members), mx, boom

    def github_org_members(self, company):
        if self.boom:
            raise self.boom
        return self.org, self.members

    def mx_ok(self, domain):
        return self.mx


def test_nothing_found_is_a_complete_answer():
    lines = C.lookup("Acme", None, FakeEnrich(), {})
    assert "[github-org] nothing found" in lines
    assert not any(l.startswith("[github-member]") for l in lines)


def test_org_and_members_are_reported_with_urls():
    fake = FakeEnrich(org="acme-inc", members=[("Pat Example", "https://github.com/pat-example")])
    lines = C.lookup("Acme", None, fake, {})
    assert any("https://github.com/acme-inc" in l and "verify before citing" in l for l in lines)
    assert "[github-member] Pat Example | https://github.com/pat-example" in lines


def test_org_with_no_public_members_says_so():
    lines = C.lookup("Acme", None, FakeEnrich(org="acme-inc"), {})
    assert "[github-member] nothing found" in lines


def test_token_is_reported_as_set_never_as_a_value():
    lines = C.lookup("Acme", None, FakeEnrich(), {"GITHUB_TOKEN": "ghp_secretvalue"})
    assert "[github-token] set" in lines
    assert not any("ghp_secretvalue" in l for l in lines)


def test_missing_token_is_reported_as_unset():
    lines = C.lookup("Acme", None, FakeEnrich(), {})
    assert any(l.startswith("[github-token] unset") for l in lines)


def test_domain_check_runs_only_when_a_domain_is_given():
    assert not any(l.startswith("[mx]") for l in C.lookup("Acme", None, FakeEnrich(mx=True), {}))
    assert "[mx] example.com | accepts mail" in C.lookup("Acme", "example.com", FakeEnrich(mx=True), {})
    assert "[mx] example.com | no MX record found" in C.lookup("Acme", "example.com", FakeEnrich(mx=False), {})


def test_main_prints_lines_and_count_and_exits_0(capsys):
    code = C.main(["Acme"], enrich=FakeEnrich(org="acme-inc"), env={})
    out = capsys.readouterr().out
    assert code == 0 and out.rstrip().endswith("line(s)")


def test_main_exits_2_when_the_lookup_fails(capsys):
    code = C.main(["Acme"], enrich=FakeEnrich(boom=RuntimeError("rate limited")), env={})
    err = capsys.readouterr().err
    assert code == 2 and "could not run" in err and "rate limited" in err
