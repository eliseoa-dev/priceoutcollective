# Contributing

We're a small team working fast against a hackathon clock. Keep it simple:

## Workflow

1. **Fork or branch.** If you have write access, branch directly:
   `git checkout -b <yourname>/<short-topic>` (e.g. `alex/rent-voucher-scenario`).
   If you don't have write access, fork the repo and branch there instead.
2. **Commit small, commit often.** Clear messages — what changed and why.
3. **Push and open a PR into `main`.** Fill in what you built and how to
   run/demo it.
4. **Get one review** from a teammate before merging if you can — otherwise
   self-merge once CI (if any) is green. We're optimizing for speed, not
   process, but a second pair of eyes catches broken demos fast.
5. **Don't force-push over someone else's branch.** If you need to update a
   PR, push new commits or rebase your own branch only.

## Ground rules

- Keep your piece self-contained where possible — read from `data/zips.csv`,
  write your outputs to `outputs/`, and avoid reaching into another
  teammate's module unless you've talked to them first.
- If you change the shared CSV schema (`data/zips.csv`), update
  `data/README.md` in the same PR and ping the team — other pieces depend
  on those column names.
- Prefer a working, ugly demo over a polished, broken one. Bar chart > no
  chart.

## Local setup

Each subfolder has its own `requirements.txt` (Python) where relevant.
General pattern:

```bash
cd policy_calculator
pip install -r requirements.txt
python run.py
```
