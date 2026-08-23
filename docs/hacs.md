# HACS notes

This repository is a standard HACS **custom integration**.

Users add it under **HACS → ⋮ → Custom repositories** as type Integration,
then download **KingSmith WalkingPad (Offline)**.

## After the first merge to `main`

HACS installs from the default branch (and from GitHub Releases, once you
publish one). Merge the integration PR before adding the custom repository.

Set these on the GitHub repo page (the API token this agent has cannot):

1. **Description:** `Offline Home Assistant integration for KingSmith WalkingPad treadmills`
2. **Topics:** `home-assistant`, `hacs`, `hacs-integration`, `walkingpad`, `kingsmith`, `bluetooth`
3. **Releases → Draft a new release** tagged `v0.1.0` after merge

Then the HACS Action can run with **no** `ignore` list, which is what
[hacs/default](https://www.hacs.xyz/docs/publish/include/) requires if you later
want it in the official store. That submission is a separate PR by the repo
owner, months of review later. Custom repository is the usual path until then.
