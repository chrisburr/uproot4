# BSD 3-Clause License; see https://github.com/scikit-hep/uproot5/blob/main/LICENSE

import pytest
import skhep_testdata

import uproot

ak = pytest.importorskip("awkward")


@pytest.mark.parametrize(
    ("entry_start", "entry_stop", "clusters"),
    [
        (0, 86, (0, 1)),
        (86, 172, (1, 2)),
        (0, 172, (0, 2)),
        (172, 200, (2, 3)),
        (50, 100, (0, 2)),
        (86, 86, (1, 2)),
    ],
)
def test_entry_stop_on_cluster_boundary(entry_start, entry_stop, clusters):
    # three clusters with first entries 0, 86, 172
    ntuple = uproot.open(
        skhep_testdata.data_path("test_index_multicluster_rntuple_v1-0-0-0.root")
    )["ntuple"]
    assert [c.num_first_entry for c in ntuple.cluster_summaries] == [0, 86, 172]

    access_log = []
    arrays = ntuple.arrays(
        entry_start=entry_start,
        entry_stop=entry_stop,
        virtual=True,
        access_log=access_log,
    )
    ak.materialize(arrays)

    assert {(a.cluster_start, a.cluster_stop) for a in access_log} == {clusters}
    assert ak.array_equal(
        ntuple.arrays(entry_start=entry_start, entry_stop=entry_stop),
        ntuple.arrays()[entry_start:entry_stop],
    )
