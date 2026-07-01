"""Tests for scripts/security/check_hf_pins.py (G1 HuggingFace revision-pin guard)."""

from __future__ import annotations

from conftest import load_training_module

_MOD = load_training_module("scripts_security_check_hf_pins", "scripts/security/check_hf_pins.py")


class TestHasRevision:
    def test_repo_tree_is_clean(self):
        # The production tree must pass its own guard; a regression here means a
        # new bare from_pretrained/snapshot_download landed.
        assert _MOD.main(["check_hf_pins.py"]) == 0

    def test_flags_bare_from_pretrained(self, tmp_path):
        root = tmp_path / "evaluation"
        root.mkdir()
        (root / "mod.py").write_text('X.from_pretrained("a/b")\n', encoding="utf-8")

        assert _MOD.main(["check_hf_pins.py", str(root)]) == 1

    def test_flags_bare_snapshot_download(self, tmp_path):
        root = tmp_path / "evaluation"
        root.mkdir()
        (root / "mod.py").write_text('snapshot_download(repo_id="c")\n', encoding="utf-8")

        assert _MOD.main(["check_hf_pins.py", str(root)]) == 1

    def test_accepts_explicit_revision(self, tmp_path):
        root = tmp_path / "evaluation"
        root.mkdir()
        (root / "mod.py").write_text('X.from_pretrained("a/b", revision=rev)\n', encoding="utf-8")

        assert _MOD.main(["check_hf_pins.py", str(root)]) == 0

    def test_accepts_kwargs_splat(self, tmp_path):
        root = tmp_path / "evaluation"
        root.mkdir()
        (root / "mod.py").write_text("hf_hub_download(**opts)\n", encoding="utf-8")

        assert _MOD.main(["check_hf_pins.py", str(root)]) == 0

    def test_excludes_test_files(self, tmp_path):
        root = tmp_path / "evaluation"
        (root / "tests").mkdir(parents=True)
        (root / "tests" / "test_x.py").write_text('X.from_pretrained("a/b")\n', encoding="utf-8")
        (root / "test_top.py").write_text('X.from_pretrained("a/b")\n', encoding="utf-8")

        assert _MOD.main(["check_hf_pins.py", str(root)]) == 0

    def test_ignores_function_definitions(self, tmp_path):
        root = tmp_path / "evaluation"
        root.mkdir()
        (root / "mod.py").write_text("def from_pretrained(cls, repo):\n    return repo\n", encoding="utf-8")

        assert _MOD.main(["check_hf_pins.py", str(root)]) == 0
