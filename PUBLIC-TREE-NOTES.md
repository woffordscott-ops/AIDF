# Public tree: what was left out

This tree was exported from commit cdba25a95b756d7b8c5d88b29e54c8f0e65a026c of a private repository (3536 tracked files, 375 exported).
Files were taken whole from that commit and left out whole; none was rewritten. The scan covered file names and bytes for the
private-identifier patterns, in raw, UTF-16 and simple-concatenation forms; it does not cover every possible spelling and it
does not change git history. Tests that read left-out files are skipped and say so.

## Directories left out (13)

Evidence archives from the private pilot: they carry local paths and the private host name, and the checks that read them are skipped in the public tree. The customer cut also leaves out the framework's own measurement runs and the records of its latest changes: they are the build record, not something a user of AIDF needs. The example profiles of the private pilot are left out as well: they name the pilot project.

## Files left out (315)

Review reports, evidence packs and task contracts that contain a local path or the private host name (found by the scan), and the private pilot's pipeline file, which holds its protected variables, runner and project path. The export tool, its manifest and its test are left out too: the manifest names the strings it searches for. Reports about this export that spell out the strings searched for are left out. The customer cut also leaves out historical reports, evidence packs, dispositions and task contracts that no test in the public tree reads, and a few tests whose inputs are among the files left out. Files that carry the private pilot project's name are left out too, with a test that needs them; the qualification, gate-checker and reference-suite tests are kept and skip the tests that read a left-out file: the scan now fails if that name is in any published file.

## Files left out by name prefix (9)

Reports, the contract-adjacent evidence pack and other files about this export itself (they spell out or discuss the strings searched for). The reports and records of the customer cut itself. The reports and records of the change that removed the pilot project's name. The reports and records of the change that stopped listing the files left out.
