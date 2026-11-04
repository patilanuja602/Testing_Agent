import pytest

from core.language_detector import (
    EXTENSION_MAP, SUPPORTED_LANGUAGES, UPLOAD_EXTENSIONS, check_source_file, detect_language, unsupported_reason,
)
from models.analysis_result import Language


@pytest.mark.parametrize("name,lang", [
    ("a.c", Language.C), ("A.C", Language.C), ("a.cpp", Language.CPP), ("x/y/a.cc", Language.CPP),
    ("a.hpp", Language.CPP), ("a.h", Language.C), ("a.hxx", Language.CPP), ("a.cxx", Language.CPP),
])
def test_detects_supported(name, lang):
    assert detect_language(name) is lang


@pytest.mark.parametrize("name", ["a.txt", "a.java", "Makefile", "a.exe", "a.xlsx", "a.js", "a.py", "A.PY", "dir/tool.py"])
def test_unsupported_is_none(name):
    assert detect_language(name) is None


def test_only_c_and_cpp_are_offered():
    assert SUPPORTED_LANGUAGES == [Language.C, Language.CPP]
    assert set(EXTENSION_MAP.values()) == {Language.C, Language.CPP}
    assert "py" not in UPLOAD_EXTENSIONS and "zip" in UPLOAD_EXTENSIONS
    assert {"c", "h", "cpp", "cc", "cxx", "hpp", "hh", "hxx"} <= set(UPLOAD_EXTENSIONS)
    assert unsupported_reason("tool.py") == "Unsupported file type '.py'"


def test_binary_empty_size_and_header_checks(tmp_path):
    binary = tmp_path / "b.c"; binary.write_bytes(b"\x00\x01\x02int main(){}")
    empty = tmp_path / "e.c"; empty.write_bytes(b"")
    good = tmp_path / "ok.c"; good.write_text("int main(void){return 0;}\n")
    header = tmp_path / "x.h"; header.write_text("int f(void);\n")
    assert not check_source_file(binary, Language.C, 1000).ok
    assert not check_source_file(empty, Language.C, 1000).ok
    assert not check_source_file(good, Language.C, 5).ok          # size limit
    assert check_source_file(good, Language.C, 1000).ok
    assert any("Header" in w for w in check_source_file(header, Language.C, 1000).warnings)
