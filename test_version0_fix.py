#!/usr/bin/env python3
"""
Test script to verify the fix for version 0 deserialization error.

This script attempts to read a branch from an LHCb ROOT file that contains
KeyedContainer objects which inherit from ObjectContainerBase (version 0).
Previously, this would fail with a DeserializationError about expected
bytes vs actual bytes read.
"""
import uproot
import sys

def test_version0_deserialization():
    """Test reading version 0 objects in TBranch context."""

    file_path = "root://x509up_u73370@xrootd-lhcb.cr.cnaf.infn.it:1094//storage/gpfs_lhcb/disk/lhcb/MC/2018/ALLSTREAMS.MDST/00207047/0000/00207047_00000034_1.allstreams.mdst"

    print("Testing version 0 object deserialization fix...")
    print(f"File: {file_path}")
    print()

    try:
        with uproot.open(file_path) as f:
            tree = f["FileRecords"]

            # Try to read KeyedContainer branches which have ObjectContainerBase (version 0)
            test_branches = [
                "_FileRecords_LumiFSRBeamCrossing.",
                "_FileRecords_LumiFSRBeam1.",
                "_FileRecords_LumiFSRBeam2.",
            ]

            for branch_name in test_branches:
                print(f"Testing branch: {branch_name}")
                branch = tree[branch_name]

                # Try to read the first entry using library="np" (needed for pointer objects)
                data = branch.array(entry_start=0, entry_stop=1, library="np")
                print(f"  ✓ Successfully read {len(data)} entries")
                print(f"  Data type: {type(data)}")
                if len(data) > 0:
                    print(f"  First entry type: {type(data[0])}")
                print()

        print("=" * 80)
        print("SUCCESS! All branches read without deserialization errors.")
        print("=" * 80)
        return True

    except uproot.deserialization.DeserializationError as e:
        print("=" * 80)
        print("FAILED! DeserializationError still occurring:")
        print("=" * 80)
        print(str(e))
        return False

    except Exception as e:
        print("=" * 80)
        print(f"ERROR: Unexpected exception: {type(e).__name__}")
        print("=" * 80)
        print(str(e))
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_version0_deserialization()
    sys.exit(0 if success else 1)
