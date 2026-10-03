# BSD 3-Clause License; see https://github.com/scikit-hep/uproot5/blob/main/LICENSE

import pytest
import skhep_testdata

import uproot


@pytest.mark.parametrize("library", ["zlib", "isal"])
def test_zlib_library_used_for_reading(monkeypatch, library):
    if library == "zlib":
        import zlib as target
    else:
        target = pytest.importorskip("isal").isal_zlib

    calls = []
    original = target.decompress

    def spy(*args, **kwargs):
        calls.append(len(args[0]))
        return original(*args, **kwargs)

    monkeypatch.setattr(target, "decompress", spy)
    monkeypatch.setattr(uproot.ZLIB, "library", library)

    with uproot.open(skhep_testdata.data_path("uproot-Zmumu-zlib.root")) as f:
        px1 = f["events"]["px1"].array(entry_stop=5, library="np")

    assert px1.tolist() == [
        -41.1952876442,
        35.1180497674,
        35.1180497674,
        34.1444372454,
        22.7835819537,
    ]
    assert len(calls) > 0
