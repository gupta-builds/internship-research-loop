"""Unit tests for .claude/skills/finding-resources/scripts/check_vault_reachability.py.
Every folder here is synthetic, built in tmp_path; no real vault or config is read."""
import importlib.util
import json
import pathlib

SCRIPT = pathlib.Path(__file__).resolve().parents[2] / ".claude/skills/finding-resources/scripts/check_vault_reachability.py"
spec = importlib.util.spec_from_file_location("check_vault_reachability", SCRIPT)
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)


def test_env_unset_is_not_found():
    ok, detail = R.check_env({})
    assert not ok and "not set" in detail


def test_env_without_marker_folder_is_not_found(tmp_path):
    ok, detail = R.check_env({"JARVIS_DIR": str(tmp_path)})
    assert not ok and "30_Order" in detail


def test_env_with_marker_folder_is_possible(tmp_path):
    (tmp_path / "30_Order").mkdir()
    ok, _ = R.check_env({"JARVIS_DIR": str(tmp_path)})
    assert ok


def test_sibling_missing_names_both_candidates(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    ok, detail = R.check_siblings(repo)
    assert not ok and "Jarvis" in detail and "jarvis-checkout" in detail


def test_sibling_folder_without_git_is_not_found(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (tmp_path / "Jarvis").mkdir()                          # a folder, but no .git
    ok, _ = R.check_siblings(repo)
    assert not ok


def test_mcp_registered_in_home_config(tmp_path):
    (tmp_path / ".claude.json").write_text(json.dumps({"mcpServers": {"jarvis": {}}}), encoding="utf-8")
    ok, detail = R.check_mcp(tmp_path, tmp_path / "repo")
    assert ok and ".claude.json" in detail


def test_mcp_bad_json_is_skipped_not_raised(tmp_path):
    (tmp_path / ".claude.json").write_text("{not json", encoding="utf-8")
    ok, _ = R.check_mcp(tmp_path, tmp_path / "repo")
    assert not ok


def test_main_exits_1_when_nothing_is_reachable(tmp_path, capsys):
    repo = tmp_path / "repo"
    repo.mkdir()
    code = R.main(env={}, home=tmp_path / "home", repo_root=repo)
    assert code == 1
    assert "NO way to reach the vault" in capsys.readouterr().out


def test_main_exits_0_and_names_the_env_way(tmp_path, capsys):
    vault = tmp_path / "vault"
    (vault / "30_Order").mkdir(parents=True)
    repo = tmp_path / "repo"
    repo.mkdir()
    code = R.main(env={"JARVIS_DIR": str(vault)}, home=tmp_path / "home", repo_root=repo)
    out = capsys.readouterr().out
    assert code == 0
    assert "JARVIS_DIR:" in out and "POSSIBLE" in out


def test_mcp_server_named_jarvis_fs_counts(tmp_path):
    (tmp_path / ".claude.json").write_text(json.dumps({"mcpServers": {"jarvis-fs": {}}}), encoding="utf-8")
    ok, _ = R.check_mcp(tmp_path, tmp_path / "repo")        # mutation check 2026-11-27: ignoring jarvis-fs left every test green
    assert ok


def test_sibling_checkout_without_a_readable_origin_says_so(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (tmp_path / "Jarvis" / ".git").mkdir(parents=True)      # a .git folder that is not a real repository, so git fails
    ok, detail = R.check_siblings(repo)
    assert ok and "(remote unknown)" in detail


def test_main_recommends_vault_list_when_only_mcp_is_registered(tmp_path, capsys):
    repo = tmp_path / "repo"
    repo.mkdir()
    home = tmp_path / "home"
    home.mkdir()
    (home / ".claude.json").write_text(json.dumps({"mcpServers": {"jarvis": {}}}), encoding="utf-8")
    assert R.main(env={}, home=home, repo_root=repo) == 0
    assert "mcp__jarvis__vault_list" in capsys.readouterr().out


def test_main_recommends_the_checkout_when_one_exists(tmp_path, capsys):
    repo = tmp_path / "repo"
    repo.mkdir()
    (tmp_path / "Jarvis" / ".git").mkdir(parents=True)
    assert R.main(env={}, home=tmp_path / "home", repo_root=repo) == 0
    assert "git diff" in capsys.readouterr().out


def test_main_names_the_env_way_in_its_recommendation(tmp_path, capsys):
    vault = tmp_path / "vault"
    (vault / "30_Order").mkdir(parents=True)
    repo = tmp_path / "repo"
    repo.mkdir()
    R.main(env={"JARVIS_DIR": str(vault)}, home=tmp_path / "home", repo_root=repo)
    assert "Read on paths under $JARVIS_DIR" in capsys.readouterr().out
