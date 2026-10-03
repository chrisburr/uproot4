# BSD 3-Clause License; see https://github.com/scikit-hep/uproot5/blob/main/LICENSE

import pytest
import skhep_testdata

import uproot

ak = pytest.importorskip("awkward")


@pytest.mark.parametrize("step_size", [30, 86, 100])
def test_iterate_reads_each_cluster_once(monkeypatch, step_size):
    # three clusters with first entries 0, 86, 172
    ntuple = uproot.open(
        skhep_testdata.data_path("test_index_multicluster_rntuple_v1-0-0-0.root"),
        array_cache=None,
    )["ntuple"]
    model = type(ntuple)

    reads = []
    original = model.read_page

    def spy(self, destination, cluster_idx, col_idx, *args, **kwargs):
        reads.append((cluster_idx, col_idx))
        return original(self, destination, cluster_idx, col_idx, *args, **kwargs)

    monkeypatch.setattr(model, "read_page", spy)

    full = ntuple.arrays()
    expected = sorted(reads)
    reads.clear()

    steps = list(ntuple.iterate(step_size=step_size))

    assert sorted(reads) == expected
    assert ak.array_equal(ak.concatenate(steps), full)


@pytest.mark.parametrize("step_size", [1, 30, 86, 100, 1000])
@pytest.mark.parametrize(("entry_start", "entry_stop"), [(None, None), (40, 190)])
@pytest.mark.parametrize("library", ["ak", "np"])
def test_iterate_steps(step_size, entry_start, entry_stop, library):
    ntuple = uproot.open(
        skhep_testdata.data_path("test_index_multicluster_rntuple_v1-0-0-0.root")
    )["ntuple"]
    start = 0 if entry_start is None else entry_start
    stop = ntuple.num_entries if entry_stop is None else entry_stop
    full = ntuple.arrays()

    steps = list(
        ntuple.iterate(
            step_size=step_size,
            entry_start=entry_start,
            entry_stop=entry_stop,
            library=library,
            report=True,
        )
    )

    assert [(r.start, r.stop) for _, r in steps] == [
        (s, min(s + step_size, stop)) for s in range(start, stop, step_size)
    ]
    for arrays, report in steps:
        if library == "np":
            arrays = ak.Array({k: ak.from_iter(v) for k, v in arrays.items()})
        assert ak.array_equal(
            arrays, full[report.start : report.stop], dtype_exact=library == "ak"
        )
