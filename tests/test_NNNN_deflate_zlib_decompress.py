# BSD 3-Clause License; see https://github.com/scikit-hep/uproot5/blob/main/LICENSE

import zlib

import pytest

import uproot


def test_deflate_decompress():
    pytest.importorskip("deflate")
    payload = bytes(range(256)) * 1000
    compressor = uproot.ZLIB(1)
    compressor.library = "deflate"
    assert compressor.decompress(zlib.compress(payload, 1), len(payload)) == payload
