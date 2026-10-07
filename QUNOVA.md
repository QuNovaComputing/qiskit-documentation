# How Qunova works in this fork

This is QuNovaComputing's fork of [Qiskit/documentation](https://github.com/Qiskit/documentation), the source of the IBM Quantum docs. We use it to prepare changes to the HI-VQE Chemistry docs, review them internally, and then send them to IBM.

This file and the `qunova/` folder are fork-only. They live on our `main` and must never be part of a PR to IBM.

Files we own:

- `docs/guides/qunova-chemistry.ipynb` (guide, includes the Changelog)
- `docs/api/functions/qunova-chemistry.mdx` (API reference)
- `docs/tutorials/qunova-hivqe.ipynb` (tutorial)

## Repositories and branches

| Name                                              | What it is                                                                                                                | Rules                                                                                                          |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `upstream` = `Qiskit/documentation`               | IBM's repository. What is on its `main` is what the docs site publishes.                                                  | We only reach it through PRs.                                                                                  |
| `origin` = `QuNovaComputing/qiskit-documentation` | Our fork.                                                                                                                 |                                                                                                                |
| `main` (fork)                                     | Our hub: IBM's docs plus fork-only files (this file and `qunova/`).                                                       | **Never use it as the head of a PR to IBM.** It carries fork-only files.                                       |
| `upstream-main` (fork)                            | A copy of IBM's `main`. It is the base of review PRs, so their **Files changed** tab shows exactly what IBM will receive. | Locked by a ruleset. Nothing can be merged or pushed into it. See [Repository settings](#repository-settings). |
| Change branch, for example `hivqe-4.0.0`          | One change to our docs, cut from IBM's `main`.                                                                            | The same branch is reviewed in the fork and then sent to IBM.                                                  |
| `pr-screenshots` (fork)                           | Before/after screenshots used in review PRs, one folder per change branch.                                                | Orphan branch with no shared history with the docs. Never part of a PR.                                        |

Set up the remotes once:

```bash
git remote add upstream https://github.com/Qiskit/documentation.git   # if missing
git fetch upstream origin
```

## How a change goes to IBM

### 1. Start from IBM's `main`

```bash
git fetch upstream
git checkout -b hivqe-<version> upstream/main
```

Do not branch from our `main`.

### 2. Edit the docs and add a Changelog entry

Every change that users will notice gets an entry in the guide's `## Changelog` section. The section sits just before "Get support". Put the newest version on top. Use plain bullets under a `### <version>` heading, with no Breaking changes or Features subheadings:

```markdown
## Changelog

### 5.0.0

- ...

### 4.0.0

- The result no longer includes `"states"` or `"eigenvector"`. ...
```

Write each entry for the reader. Say what changed in the function's inputs, outputs, or behaviour, and what they need to do about it.

If you edit a notebook's outputs by hand instead of re-running it, say so in the review PR. IBM's CI does not execute the two Qunova notebooks: they are on the exclude list in `scripts/config/notebook-testing.toml`.

**If you change code in a notebook, run that cell against the deployed function.** Nothing else will, and code that reads correctly can still fail. For example, the guide's download example once opened a file under a name `file_download` never saved, and a rename once changed `run()` keyword names that the function rejects. Run a copy outside the repo, so the docs' outputs don't change by accident.

**The guide's qubit rule is tested in QunovaPulsar.** "Check the size before you run" gives readers the rule as a table (2 × the orbitals AVAS selects, else 2 × `len(active_orbitals)`, else 2 × the basis size), plus `estimate_only` for an exact figure. `estimate_only` is billed as a run at the size it is submitted at, so the guide says to submit it at `"s"`. QunovaPulsar's `qiskit_functions/tests/test_doc_sizing.py` writes the table as code and checks it against the function's own sizing. If you change the table, update that test. If the test fails after a function change, the table has to change.

### 3. Run the checks

IBM's CI does not run in the fork, so run its checks locally. These are the content checks from the Lint job in `.github/workflows/main.yml`. You need `npm ci` once, and [uv](https://docs.astral.sh/uv/) for the notebook tools:

```bash
npm run check:internal-links -- --current-apis --dev-apis --historical-apis --qiskit-legacy-release-notes
npm run check:stale-images
npm run check:markdown -- --apis
npm run check:spelling
npm run check:qiskit-bot
npm run check:fmt
npm run check:orphan-pages -- --apis
uvx ruff@0.7.1 format --check docs/guides/qunova-chemistry.ipynb docs/tutorials/qunova-hivqe.ipynb
uvx --from squeaky==0.7.0 squeaky --check --no-advice docs/guides/qunova-chemistry.ipynb docs/tutorials/qunova-hivqe.ipynb
uvx --from ./scripts/notebook-normalizer qiskit-docs-notebook-normalizer --check
```

With the preview running (`./start`), also check that the changed pages render. This needs `npx playwright install firefox` once:

```bash
printf '%s\n' docs/guides/qunova-chemistry.ipynb docs/api/functions/qunova-chemistry.mdx docs/tutorials/qunova-hivqe.ipynb > /tmp/changed.txt
npm run check:pages-render -- --from-file /tmp/changed.txt
npm run check:katex-render -- --from-file /tmp/changed.txt
```

Also confirm that the branch only touches our files:

```bash
git diff --stat upstream/main...HEAD
```

### 4. Capture before/after screenshots

Reviewers include people who do not read notebook JSON. The review PR shows the rendered pages instead.

1. Start the preview with `./start` (see [Local preview](#local-preview)). It mounts the working tree, so whatever is checked out is what it shows.
2. Write a shots file listing the sections that changed. `qunova/shots/hivqe-4.0.0.json` is an example.
3. Capture both versions. The script lives on our `main`, so copy it out first:

   ```bash
   S=$(mktemp -d)
   git show origin/main:qunova/screenshots.py > $S/screenshots.py
   git checkout hivqe-<version>
   uv run --with playwright python $S/screenshots.py --shots <shots.json> --label after --out $S/shots
   git checkout upstream/main          # wait a few seconds for the preview to reload
   uv run --with playwright python $S/screenshots.py --shots <shots.json> --label before --out $S/shots
   git checkout hivqe-<version>
   ```

4. Commit the images to `pr-screenshots` under a folder named after the branch:

   ```bash
   git worktree add $S/wt origin/pr-screenshots
   mkdir -p $S/wt/hivqe-<version> && cp $S/shots/*.png $S/wt/hivqe-<version>/
   git -C $S/wt add -A && git -C $S/wt commit -m "Add hivqe-<version> screenshots"
   git -C $S/wt push origin HEAD:pr-screenshots
   git worktree remove $S/wt
   ```

5. Reference them in the PR description as
   `https://github.com/QuNovaComputing/qiskit-documentation/blob/pr-screenshots/hivqe-<version>/<name>-after.png?raw=true`.

### 5. Open the review PR

Make sure `upstream-main` is current first. If IBM's `main` has moved on, refresh it as described in [Repository settings](#repository-settings).

```bash
git push -u origin hivqe-<version>
gh pr create --repo QuNovaComputing/qiskit-documentation \
  --base upstream-main --head hivqe-<version> \
  --reviewer supalert-qunova \
  --title "[Review before IBM] HI-VQE docs for <version>"
```

The PR description should contain:

- A "Do not merge" note at the top.
- What changes for users (the Changelog entry).
- Before/after screenshots for each changed section.
- Anything that needs a decision.
- The link that opens the PR to IBM (see step 7).

[#6](https://github.com/QuNovaComputing/qiskit-documentation/pull/6) is the reference example.

### 6. Review and approval

- **`supalert-qunova` is a required reviewer on every PR that changes what HI-VQE users read**: the guide, the tutorial, the API reference, and the Changelog, including review PRs before IBM. Add whoever owns the feature as well.
- Fork-internal PRs don't need `supalert-qunova`. That covers this file, the `qunova/` scripts, syncing with IBM's `main`, and CI or repository settings.
- To approve, a reviewer opens **Files changed**, clicks **Review changes** (or **Submit review**), chooses **Approve** and submits. The PR author cannot approve their own PR.
- Fixes go on the same branch as new commits. The review PR updates by itself.
- Do not merge the review PR. The `upstream-main` ruleset blocks it anyway.

### 7. Send the same branch to IBM

Open the PR from the same branch, either through this link:

```
https://github.com/Qiskit/documentation/compare/main...QuNovaComputing:qiskit-documentation:hivqe-<version>?expand=1
```

Or use the GitHub UI: on Qiskit/documentation, go to **Pull requests → New pull request → compare across forks**. Set the head repository to `QuNovaComputing/qiskit-documentation` and pick the change branch, **not `main`**.

Sign IBM's contributor license agreement (CLA) when the bot asks. It can be done after the PR is opened.

After that:

- **CI may wait for approval.** If this is the author's first PR to Qiskit/documentation, GitHub holds IBM's CI until a maintainer clicks **Approve and run**. The checks show `action_required`, and the required **Lint** and **Execute notebooks** checks show "Expected — Waiting for status to be reported". Ask in the Slack channel `qunova-ibm-quantum-partnership`; @abbycross reviewed and merged our last PR (#5425), and @HuangJunye is our contact. Authors with a merged PR get CI straight away.
- **Expected results.** Lint should pass if step 3 passed. Execute notebooks skips our two notebooks, because they are on IBM's exclude list. PR preview skips for PRs from forks.
- **Review fixes** go on the same branch as new commits, and the IBM PR picks them up.

### 8. After IBM merges

1. Close the review PR in the fork, if it is still open.
2. Bring IBM's `main` into our `main`, either with the **Sync fork** button on GitHub or with:

   ```bash
   git checkout main && git pull origin main
   git merge upstream/main && git push origin main
   ```

   > [!WARNING]
   > On **Sync fork**, choose **Update branch** (a merge), **never Discard commits**. Our `main` carries fork-only commits that IBM does not have: this file and `qunova/`. Discarding deletes them. Do not force-push IBM's `main` over ours for the same reason. (Discarding was fine once, when every extra commit on our `main` was already in IBM's history under a different hash. That is no longer the case.)

3. Refresh `upstream-main` before the next review PR.

## Repository settings

Changing these needs repository admin rights.

- **Disabled workflows: "PR preview" and "Main branch preview".** Both build IBM's preview site from a private IBM image (`icr.io/qc-open-source-docs-prod/preview-builder`) and need IBM registry credentials. They can never succeed in the fork. IBM's other jobs (Lint, Execute notebooks) skip on purpose outside the Qiskit organization. None of this affects PRs to IBM, which run IBM's own CI.
- **Ruleset "Lock upstream-main"** (id `24623094`). It blocks updates, deletion, and force pushes to `upstream-main`, with no bypass. To refresh the branch:

  ```bash
  R=repos/QuNovaComputing/qiskit-documentation/rulesets/24623094
  gh api -X PUT $R -f enforcement=disabled
  git fetch upstream && git push origin upstream/main:refs/heads/upstream-main
  gh api -X PUT $R -f enforcement=active
  ```

- **Branches are deleted when a PR merges.** If a branch disappears by mistake, use **Restore branch** on the PR.

## Local preview

```bash
./start          # then open http://localhost:3000
./start --apis   # also include the non-functions API docs
```

- Docker must be running. On macOS, use Docker Desktop.
- The preview image is published for amd64 and arm64, so `./start` runs natively on Apple Silicon too. (Older images were amd64-only, and our `main` pinned `--platform linux/amd64` until #11.)
- If port 3000 is in use, an earlier preview is still running. Stop it with `docker ps` and `docker stop <id>`.

## Status

Last updated 2026-10-07.

- **4.0.0:** approved in [#6](https://github.com/QuNovaComputing/qiskit-documentation/pull/6) (now closed). Sent to IBM as [Qiskit/documentation#5758](https://github.com/Qiskit/documentation/pull/5758) from `hivqe-4.0.0`. CLA is signed. CI is waiting for a maintainer to approve it, since this is the author's first PR there. Two fixes found while running the guide against the deployed 4.0.0 function went in before sending, and onto our `main` through #8 and #9: the results-file download now passes `target_name`, and the licensing example uses `backend_name` instead of `ibm_torino`.
- **5.0.x:** [#3](https://github.com/QuNovaComputing/qiskit-documentation/pull/3) predates this process. It is stacked on our `main` and has no 5.0.x Changelog entry yet. After IBM merges 4.0.0, move it to a branch cut from IBM's `main`, add the Changelog entry, and review it as above. Its error table lists 4630 for an unreadable licence, which QunovaPulsar has but no released function version does yet (5.0.2 still returns 1219). Send it only once that version ships.
- **Planned:** automate steps 3 and 4 as fork-only GitHub Actions. They would run the checks, post the screenshots as a PR comment, and fail when a branch would carry fork-only files to IBM.
