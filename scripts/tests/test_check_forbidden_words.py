import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "cfw", Path(__file__).resolve().parent.parent / "check-forbidden-words.py"
)
assert _spec and _spec.loader
cfw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cfw)


def test_detecte_un_classement(tmp_path: Path) -> None:
    (tmp_path / "a.ts").write_text('export const t = "le candidat le plus crédible";\n')
    assert len(cfw.scan([tmp_path])) == 1


def test_exception_assumee_listee(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("Ne jamais dire meilleur. <!-- mots-interdits: autorise -->\n")
    allowed: list[str] = []
    assert cfw.scan([tmp_path], allowed) == []
    assert len(allowed) == 1


def test_texte_neutre(tmp_path: Path) -> None:
    (tmp_path / "a.ts").write_text('export const t = "Proximité avec chaque candidat";\n')
    assert cfw.scan([tmp_path]) == []


def test_ignore_les_caches_compiles(tmp_path: Path) -> None:
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "app.cpython-312.pyc").write_bytes(b"\xcb\x0d\x0d\x0a meilleur")
    assert cfw.scan([tmp_path]) == []
