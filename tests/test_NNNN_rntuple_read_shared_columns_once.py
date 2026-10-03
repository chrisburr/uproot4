# BSD 3-Clause License; see https://github.com/scikit-hep/uproot5/blob/main/LICENSE

import pytest
import skhep_testdata

import uproot

ak = pytest.importorskip("awkward")


@pytest.mark.parametrize("virtual", [False, True])
def test_shared_column_read_once(monkeypatch, virtual):
    # nMuon is the cardinality of the collection whose offsets also index
    # Muon_pt, so both form keys are backed by the same column
    ntuple = uproot.open(
        skhep_testdata.data_path(
            "Run2012BC_DoubleMuParked_Muons_1000evts_rntuple_v1-0-0-0.root"
        ),
        array_cache=None,
    )["Events"]
    model = type(ntuple)

    reads = []
    original = model.read_cluster_range

    def spy(self, col_idx, *args, **kwargs):
        reads.append(col_idx)
        return original(self, col_idx, *args, **kwargs)

    monkeypatch.setattr(model, "read_cluster_range", spy)

    arrays = ntuple.arrays(filter_name=["nMuon", "Muon_pt"], virtual=virtual)
    ak.materialize(arrays)

    assert sorted(reads) == sorted(set(reads))
    assert ak.num(arrays.Muon_pt).tolist() == arrays.nMuon.tolist()
