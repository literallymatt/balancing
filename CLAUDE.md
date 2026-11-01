# balancing

GitHub (`literallymatt/balancing`) is the single source of truth for this code.

## Keeping copies in sync

- **Cloud sessions:** edit the code only in a clone of this repo. After every
  change, commit and push it to GitHub (branch and PR, merged to `main`) before
  calling the work done. Never leave changes only in a cloud container or in a
  shared project folder.
- **Merging:** merge your own PRs as soon as the work is done and checks pass.
  Don't wait for Matt to review or merge.
- **Matt's machines:** before generating data locally, pull the latest
  `main` first (`git pull origin main`), then run.
  - Mac: `/Users/matt/Documents/code/balancing-github` is the clone of this repo.
    The separate `/Users/matt/Documents/code/balancing` folder is a different,
    unrelated project with uncommitted work, so don't touch it.
  - Windows: `C:\Users\matth\Documents\code\balancing`.

## bm-charts

Run from inside `bm-charts/`, not the repo root. A uv workspace in a parent
folder on Windows breaks uv otherwise.

```bash
cd bm-charts
uv sync
uv run bm-charts    # charts and CSVs go to bm-charts/output/
uv run pytest       # offline tests against a mock API
```

The Elexon BMRS API (`data.elexon.co.uk`) is blocked from the cloud
environment, so live data runs happen on Matt's machine.
