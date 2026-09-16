# Review checkpoint — 2026-09-16

This checkpoint preserves the reviewed Bag/BagNode contracts, compatibility
methods, regression tests and migration documentation. It is not a release;
the package version is unchanged.

Validation: 920 tests passed (42 warnings). Seven SIM118 lint findings in
unchanged directory-resolver test assertions were already present at HEAD;
they inspect the keys API explicitly. No new lint findings were introduced.

The readonly resolver cache bug fix is included. Its JavaScript counterpart
is not yet implemented. Integration still has 33 existing failed parity/audit
tests requiring classification; see the companion integration checkpoint.
Browser acceptance and the final cross-repository review remain outstanding.
