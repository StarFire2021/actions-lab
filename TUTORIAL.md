# GitHub Actions, hands on

A nine-lab walkthrough that starts with a workflow that does nothing useful and
ends with reusable workflows, approval gates, and a tag-triggered release.

Everything here runs against `pricekit`, the small Python package in this repo.
It exists only to give CI something real to do: pure functions, a test suite
that runs in under a second, a linter, and a CLI that produces a file worth
uploading.

**How to use this.** Do one lab per sitting. Each lab has a goal, the file to
add, things to actually look at in the UI, and exercises. Do the exercises —
they are where the learning happens, because most of them make something break
on purpose. Answers are at the bottom of each lab.

---

## Lab 0 — Get the repo onto GitHub

```bash
cd actions-lab
git init
git add .
git commit -m "Initial commit: pricekit"
```

Create an empty repository on GitHub (no README, no .gitignore — you already
have them), then:

```bash
git remote add origin git@github.com:<you>/actions-lab.git
git branch -M main
git push -u origin main
```

**If you push over HTTPS with a personal access token**, the token needs the
`workflow` scope before you can add anything under `.github/workflows/`. Without
it the push is rejected with a confusing message about refusing to update
workflow files. SSH keys have no such restriction.

Verify the project works locally first, so that when CI fails you know it is CI
and not your code:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest          # 32 passed
ruff check .    # All checks passed!
pricekit data/sample_prices.csv
```

### Set up your editor before Lab 1

This is the highest-leverage thing in the whole tutorial. In VS Code install the
**GitHub Actions** extension (`github.vscode-github-actions`). It applies the
workflow JSON schema to anything under `.github/workflows/`, which gives you
autocomplete on every key and a red squiggle on invalid ones. Most early
frustration with Actions is typos and wrong nesting, and this removes nearly all
of it.

Optionally also install `actionlint`, a static checker that catches things the
schema cannot — bad `runs-on` labels, shell bugs inside `run:` blocks, and
expressions referencing contexts that do not exist at that point:

```bash
# macOS: brew install actionlint     Go: go install github.com/rhysd/actionlint/cmd/actionlint@latest
actionlint
```

---

## Lab 1 — Hello, Actions

**Goal:** see the trigger → runner → log loop with nothing else in the way.

```bash
mkdir -p .github/workflows
cp labs/lab01-hello.yml .github/workflows/hello.yml
git add .github/workflows/hello.yml
git commit -m "ci: hello workflow"
git push
```

Go to the **Actions** tab, pick "Hello" in the left sidebar, and click **Run
workflow**. Then open the run and expand each step.

### What to look at

- **There is no checkout step.** Look at the "Prove the workspace is empty"
  output: the directory is empty. A fresh runner has no idea what repository
  triggered it. Forgetting `actions/checkout` is the single most common beginner
  error, and this is what it looks like.
- **`run:` is just bash.** `whoami`, `nproc`, `df` all work. There is no special
  Actions command language to learn — anything installed on the machine is
  available.
- **The context dump.** The final step prints the entire `github` context as
  JSON. Skim it. That object is where `github.ref`, `github.sha`,
  `github.event.*` and everything else you will reference later comes from.
  Whenever you are unsure what is available, print `toJSON(github)` and read it.
- **Set-up and Complete job steps.** You did not write these. The runner adds
  them.

### Exercises

1. Add a step that prints `${{ github.event.repository.default_branch }}`.
   Then add one that prints `${{ github.event.pull_request.title }}` and run
   the workflow manually. What happens, and why?
2. Add `- run: exit 1` in the middle, then a step after it. Push and run.
   Does the last step execute?
3. Change `runs-on` to `windows-latest` and re-run. Which steps break?

<details>
<summary>Answers</summary>

1. The default branch prints fine. The PR title prints as an empty string —
   `workflow_dispatch` events have no `pull_request` object, and referencing a
   missing property yields empty rather than erroring. This is why `if:` guards
   on event type matter.
2. No. Every step carries an implied `if: success()`, so a failure short-circuits
   everything after it. Add `if: always()` to the last step and it runs.
3. `whoami`/`nproc`/`df` fail — the default shell on Windows runners is
   PowerShell, not bash. Fix with `shell: bash` on the step, or a
   `defaults: { run: { shell: bash } }` block.

</details>

---

## Lab 2 — Real CI

**Goal:** the smallest workflow that is genuinely useful.

```bash
cp labs/lab02-ci.yml .github/workflows/ci.yml
git add .github/workflows/ci.yml
git commit -m "ci: run tests on push and PR"
git push
```

### What to look at

- The run now takes 30–60 seconds, nearly all of it `pip install`. Remember that
  number; Lab 5 cuts it.
- `actions/setup-python@v6` — open the log for that step. It reports which
  interpreter it found and where it put it. On `ubuntu-latest` several Python
  versions are preinstalled, so this often just selects rather than downloads.
- The green checkmark now appears next to your commit in the repo view and on
  any pull request.

### Prove the PR flow works

```bash
git switch -c break-something
# edit src/pricekit/core.py: change max_drawdown's `worst = 0.0` to `worst = 99.0`
git commit -am "break drawdown"
git push -u origin break-something
```

Open a PR. Watch the check go red, then open the run and read the pytest output
inline. Fix it, push again, watch it go green. That loop — red, read, fix,
green — is the entire day-to-day experience of CI.

### Exercises

1. Delete the `- uses: actions/checkout@v7` line and push. Read the error
   carefully. Restore it.
2. Split lint into its own job (`lint:`) alongside `test:`. Do they run in
   sequence or at the same time? Does the lint job need its own checkout?
3. Add `- run: echo "$(pwd)" && ls -la` after checkout. Where exactly does your
   code land?

<details>
<summary>Answers</summary>

1. `pip install -e ".[dev]"` fails because there is no `pyproject.toml` — the
   directory is empty.
2. They run in parallel, because jobs are parallel by default. And yes, the lint
   job needs its own `checkout` and its own `setup-python`: separate job means
   separate VM, nothing is shared.
3. `/home/runner/work/actions-lab/actions-lab`, also available as
   `$GITHUB_WORKSPACE`.

</details>

---

## Lab 3 — Triggers, filters, and concurrency

**Goal:** stop wasting runner minutes, and stop overlapping runs.

```bash
cp labs/lab03-triggers.yml .github/workflows/ci.yml
git commit -am "ci: path filters, concurrency, permissions"
git push
```

Three additions worth understanding:

**`paths-ignore`** — a README edit no longer triggers CI. Test it: commit a
change to `README.md` alone and confirm nothing runs.

**`concurrency`** — the group expression `ci-${{ github.ref }}` means one slot
per branch. A new push cancels the in-flight run on that branch but leaves other
branches alone. Test it by pushing twice in quick succession and watching the
first run go grey with "Cancelled". For deploy workflows you invert this
(`cancel-in-progress: false`) so deploys queue rather than getting killed
mid-flight.

**`permissions: contents: read`** — strips the automatic token down to
read-only. Declaring a permissions block is all-or-nothing: anything you do not
list is set to `none`, not left at the default.

Also note the `workflow_dispatch` input and how it is consumed:
`pytest ${{ inputs.verbose && '-vv' || '' }}`. That is the ternary idiom —
Actions has no `if/else` in expressions, so `&&` / `||` short-circuiting is
what people use.

### Exercises

1. Push a commit that changes only `README.md`. Confirm nothing runs. Now push
   one that changes both `README.md` and `src/pricekit/core.py`. Does it run?
2. Trigger the workflow manually with `verbose` checked. Find the `-vv` output.
3. Push three commits in 20 seconds. Count the runs that survive.
4. Change `concurrency.group` to a constant string like `ci`. Push to two
   branches at once. What happens, and why is that usually wrong?

<details>
<summary>Answers</summary>

1. Yes, it runs. `paths-ignore` skips only when *every* changed file matches.
2. Individual test names appear instead of dots.
3. One — the first two are cancelled.
4. All branches share one slot, so pushing to a feature branch cancels CI on
   main. The `${{ github.ref }}` in the group is what keeps branches isolated.

</details>

---

## Lab 4 — Matrix builds

**Goal:** test many combinations from one definition.

```bash
cp labs/lab04-matrix.yml .github/workflows/ci.yml
git commit -am "ci: matrix across OS and Python versions"
git push
```

This expands to ten jobs. Look at the Actions tab — you get a row per
combination, each on its own fresh runner, all running at once.

### What to look at

- **`fail-fast: false`.** With the default (`true`), one failure cancels the
  other nine and you learn nothing. Almost always set it to false.
- **`exclude` and `include`.** `exclude` trims combinations out of the grid.
  `include` adds a combination, or — as used here — attaches an extra variable
  (`coverage: true`) to one existing leg. The `if: matrix.coverage` step then
  runs on that leg only.
- **`name:` with an expression.** Without it, ten jobs all named "test" is
  unreadable. With it you get "py3.12 on ubuntu-latest".
- **The `ci-ok` job.** Branch protection rules require naming specific checks,
  which is painful when the matrix changes. A single aggregate job that depends
  on the matrix and asserts `needs.test.result == 'success'` gives you one stable
  check name to protect. Note it needs `if: always()`, or it would be skipped
  when the matrix fails — which reports as neutral, not red.

### Exercises

1. Quote-strip a version: change `'3.10'` to `3.10` (no quotes). Push. What
   Python actually gets installed?
2. Set `fail-fast: true` and break one test. How many jobs complete?
3. Remove `if: always()` from `ci-ok`, break a test, and look at the check status
   reported on the commit.
4. Add `max-parallel: 2` under `strategy`. Watch the queueing behaviour.

<details>
<summary>Answers</summary>

1. YAML parses `3.10` as the float 3.1, so setup-python tries to install Python
   3.1 and fails. Always quote version strings. This is the most common YAML
   gotcha in Actions.
2. The failing one plus whatever had already finished; the rest are cancelled.
3. `ci-ok` is skipped rather than failed. A skipped required check can let a
   broken PR appear mergeable — the exact bug `if: always()` prevents.
4. Only two matrix legs run at a time. Useful when jobs contend for a shared
   external resource.

</details>

---

## Lab 5 — Caching and job summaries

**Goal:** make runs fast, and make results readable without opening logs.

```bash
cp labs/lab05-cache-summary.yml .github/workflows/ci.yml
git commit -am "ci: caching and job summary"
git push
```

Push twice. Compare the install time on run 1 versus run 2, and find the line in
the cache step's log that says whether it was restored.

### The key design

```yaml
key: ruff-${{ runner.os }}-${{ hashFiles('pyproject.toml') }}
restore-keys: |
  ruff-${{ runner.os }}-
```

`hashFiles()` hashes the file's contents, so the key changes exactly when your
dependencies change. `restore-keys` is a prefix fallback: on an exact miss, it
restores the most recent cache starting with that prefix, so you re-download
only what is new instead of everything.

Two rules that will save you hours:

- **A cache must never be load-bearing.** Caches expire (7 days unused), get
  evicted (10 GB per repo), and can be missing entirely on a first run. If your
  build only works with a warm cache, it is broken.
- **Caches are immutable once written.** You cannot update a cache under an
  existing key. That is why the key contains a hash rather than something
  static.

### Job summaries

Anything appended to `$GITHUB_STEP_SUMMARY` renders as markdown at the top of
the run page. This lab writes both the tail of the pytest output and the price
report table. It is by far the most underused feature in Actions — instead of
"check the logs," a teammate sees the result immediately.

### Exercises

1. Change a dependency in `pyproject.toml` and push. Does the cache hit?
   Which key was restored?
2. Delete the cache from **Actions → Caches** in the repo sidebar, then push.
   Compare the timing.
3. Write the max drawdown to the summary with a warning emoji if it exceeds 10%.
4. Remove `if: always()` from the summary step, then break a test. Does the
   summary still appear?

<details>
<summary>Answers</summary>

1. Exact key misses; the `restore-keys` prefix hits, so you get a partial warm
   start. The log names which key it fell back to.
2. Back to cold-cache timing.
3. Use a shell conditional inside the block that writes to `$GITHUB_STEP_SUMMARY`.
4. No — the implied `success()` skips it. Summaries are most valuable on failure,
   so they nearly always want `if: always()`.

</details>

---

## Lab 6 — Artifacts, dependencies, and job outputs

**Goal:** move data between jobs, which is the thing people find most
counterintuitive.

```bash
cp labs/lab06-artifacts.yml .github/workflows/report.yml
git add .github/workflows/report.yml
git commit -m "ci: report workflow with artifacts"
git push
```

Trigger it manually from the Actions tab.

### What to look at

- **Two jobs, one file passed between them.** `build` writes
  `reports/summary.md` and uploads it; `publish` downloads it into `incoming/`.
  Delete the download step and watch `publish` fail to find the file — that is
  the ephemeral-runner model made concrete.
- **The artifact appears at the bottom of the run summary page** as a
  downloadable zip. This is how you get files out of CI: coverage reports,
  built wheels, screenshots from a failed browser test.
- **The two-hop output chain.** A step writes to `$GITHUB_OUTPUT` with an `id`;
  the job promotes it under `outputs:`; the downstream job reads it via
  `needs.build.outputs.drawdown`. All three links are required.
- **`if: failure()` on the debug upload.** Break the report step on purpose and
  confirm the debug artifact appears. When you cannot SSH into the runner, this
  is your debugging channel.
- **The schedule block.** It will not fire until this file is on your default
  branch — `schedule` and `workflow_dispatch` only ever read from the default
  branch. And GitHub does not guarantee punctual execution; under load, cron
  runs can be delayed by many minutes. Never build something that needs a
  scheduled workflow to fire at an exact moment.

### Exercises

1. Delete the `download-artifact` step. What is the error in `publish`?
2. In `build`, add a step after the upload that deletes `reports/`. Does
   `publish` still work? What does that tell you about when upload happens?
3. Lower the gate threshold to `0.05` so it fails. Does the artifact still get
   uploaded?
4. Add a third job that needs both `build` and `publish`. Then make `publish`
   fail and observe whether job three runs.

<details>
<summary>Answers</summary>

1. `cat: incoming/summary.md: No such file or directory` — the second runner
   never had the file.
2. Yes. Upload copies to GitHub's storage at the moment the step runs; deleting
   the local copy afterwards is irrelevant.
3. Yes — the upload already happened in the earlier job. Failure gates should sit
   after artifact upload for exactly this reason.
4. It is skipped. Add `if: always()` and it runs; then inspect
   `needs.publish.result` to branch on what actually happened.

</details>

---

## Lab 7 — Permissions, secrets, and injection

**Goal:** understand the security model by exercising it.

```bash
cp labs/lab07-permissions-secrets.yml .github/workflows/pr-report.yml
git add .github/workflows/pr-report.yml
git commit -m "ci: PR report comment"
git push
```

Then open a pull request and watch a comment appear on it.

### What to look at

- **Permission granted at the job level, not the workflow level.** The file
  defaults to `contents: read`; only the `comment` job gets
  `pull-requests: write`. This is the pattern to internalize: default to nothing,
  grant narrowly where needed.
- **`secrets.GITHUB_TOKEN` is automatic.** You never create it. It is minted per
  run, scoped to this repository, and expires when the run ends. The `gh` CLI
  picks it up from `GH_TOKEN`.
- **The injection comment.** Read it carefully. This line is a real
  vulnerability:

  ```yaml
  - run: echo "Title: ${{ github.event.pull_request.title }}"
  ```

  Expressions are interpolated into the shell script *before* bash sees it, so a
  PR titled with backticks and a command executes on your runner with your
  token. The fix is to pass it through `env:`, where it becomes a value bash
  reads rather than code bash parses. Treat every `github.event.*` field that a
  stranger can control — titles, branch names, commit messages, issue bodies —
  as hostile.

- **Masking is literal.** Add a repository secret named `DEMO_SECRET`, re-run,
  and look at the output: the direct echo shows `***`, but the base64-encoded
  version leaks the value in plain sight. Masking is string replacement, not
  taint tracking.

### Also worth knowing

Secrets are not passed to workflows triggered by pull requests from forks. That
is deliberate, and it is why you will see people reach for `pull_request_target`
— which runs with the *base* repository's token and secrets. As of June 2026,
`actions/checkout` refuses by default to check out fork PR code under
`pull_request_target` precisely because that combination is the classic
"pwn request" vulnerability. If a tutorial tells you to use it, treat that as a
red flag.

### Exercises

1. Remove `pull-requests: write` from the job. What is the exact error from
   `gh pr comment`?
2. Open a PR titled with a backtick command substitution, using the unsafe line
   from the comment. Confirm it executes. Then switch to the `env:` form and
   confirm it does not.
3. Set the workflow-level block to `permissions: {}` and see which steps break.
4. Add a secret whose value is a common word like `test`. Where does `***` start
   showing up in your logs?

<details>
<summary>Answers</summary>

1. HTTP 403 from the API. Token permissions are enforced server-side, not by the
   action.
2. This is the whole point of the lab. Do it in a throwaway repo.
3. Checkout fails first — it needs `contents: read`.
4. Everywhere, including in unrelated words. Masking is naive substring
   replacement, which is why short or common secret values make logs unreadable.

</details>

---

## Lab 8 — Composite actions and reusable workflows

**Goal:** stop repeating yourself, and understand which of the two mechanisms
fits which situation.

```bash
mkdir -p .github/actions/setup-project
cp labs/lab08-composite-action.yml .github/actions/setup-project/action.yml
cp labs/lab08-reusable-workflow.yml .github/workflows/reusable-test.yml
cp labs/lab08-caller.yml .github/workflows/ci.yml
git add .github .
git commit -m "ci: composite action and reusable workflow"
git push
```

### The distinction

|  | Composite action | Reusable workflow |
|---|---|---|
| Lives at | `.github/actions/<name>/action.yml` | `.github/workflows/<name>.yml` |
| Called with | `uses:` at **step** level | `uses:` at **job** level |
| Bundles | steps | whole jobs |
| Chooses runner | no, inherits the caller's | yes, defines its own `runs-on` |
| Declares triggers | no | yes: `on: workflow_call` |

Rule of thumb: deduplicating a few steps → composite action. Deduplicating whole
jobs, including runner and permissions → reusable workflow.

### What to look at

- **The caller job has no `steps:` and no `runs-on:`.** `uses:` at job level
  replaces the entire job body. This looks wrong the first time you see it.
- **Composite `run:` steps require `shell:`.** It is optional in a workflow and
  mandatory in a composite action. Omit it and you get an error that does not
  explain itself.
- **The path form `./.github/actions/setup-project` needs checkout first.** A
  local action cannot be loaded from a repo that has not been cloned yet, which
  is why the caller checks out before using it.
- **Matrix over a reusable workflow.** The caller runs the reusable workflow
  three times, once per Python version, and passes `run-lint` only for 3.13.
  This composes further than it looks.
- **`secrets: inherit`.** Passes everything through. You can also name secrets
  individually, which is better practice for anything shared across repos.

### Exercises

1. Delete `shell: bash` from the composite action. Read the error.
2. Add an output to the composite action reporting the interpreter path and
   print it in the calling job.
3. Add `runs-on: ubuntu-latest` to the `test-matrix` job in the caller. What
   does the validator say?
4. Move the reusable workflow to a separate public repository and call it as
   `owner/repo/.github/workflows/reusable-test.yml@main`.

<details>
<summary>Answers</summary>

1. "Required property is missing: shell". Composite steps have no default shell.
2. `outputs.python-path` is already declared in the action; reference it as
   `steps.<id>.outputs.python-path` in the calling job.
3. Invalid — you cannot set `runs-on` on a job that uses a reusable workflow.
   The callee decides its own runner.
4. This is how organizations share one CI definition across dozens of repos.
   Note that the ref (`@main`, or better, `@<sha>`) is required.

</details>

---

## Lab 9 — Environments, approval gates, and releases

**Goal:** a manual approval gate and a tag-triggered release.

First create the environment: **Settings → Environments → New environment**,
name it `production`, and add yourself under "Required reviewers."

```bash
cp labs/lab09-release.yml .github/workflows/release.yml
git add .github/workflows/release.yml
git commit -m "ci: release workflow"
git push
```

Run it manually with `dry-run` checked. The `build` job completes, then
`publish` **pauses** and the run page shows a "Review deployments" button. That
is the approval gate — it is a first-class feature, not something you bolt on.

Then try the real path:

```bash
git tag v0.1.0
git push origin v0.1.0
```

### What to look at

- **`github.ref_type` and `github.ref_name`.** On a tag push, `ref_type` is
  `tag` and `ref_name` is `v0.1.0`. The version check compares that against
  `pricekit.__version__` and fails the build on a mismatch, which prevents the
  classic "tagged v0.2.0 but shipped 0.1.0" mistake.
- **`::error::` annotations.** The version-mismatch line emits one. Annotations
  render inline on the run page rather than being buried in logs. The full set
  of these workflow commands is short: `error`, `warning`, `notice`, `group`,
  `endgroup`, `add-mask`.
- **`contents: write` on the publish job only.** Creating a release requires
  write access; the build job never gets it.
- **`id-token: write`.** Not repository access — it lets the job mint an OIDC
  token for authenticating to AWS, GCP, or PyPI trusted publishing without
  storing long-lived credentials. This is the modern way to deploy from Actions,
  and it is strictly better than putting an access key in a secret.

### Exercises

1. Bump `__version__` to `0.2.0` but tag `v0.1.1`. Confirm the build fails with
   the annotation.
2. Add a "wait timer" of 5 minutes to the environment and re-run.
3. Add an environment-scoped secret and confirm the `build` job cannot see it
   while `publish` can.
4. Add `if: github.repository == 'you/actions-lab'` to the publish job. Why is
   that useful on a repo people fork?

<details>
<summary>Answers</summary>

1. The `::error::` shows on the summary page with the mismatch.
2. `publish` sits in a timed wait before the reviewer prompt appears.
3. Environment secrets are only injected into jobs that declare that
   environment. This is a real isolation boundary, not just organization.
4. Forks running your release workflow against their own repo is noise at best
   and confusing at worst.

</details>

---

## Where to go next

You now have hands-on exposure to roughly ninety percent of what you will ever
write. The remaining things, in rough order of how likely you are to want them:

- **`services:`** — sidecar containers on the job's network, for integration
  tests that need Postgres or Redis. Add health-check options or your tests will
  race the database's startup.
- **`container:`** — run all steps inside a Docker image instead of on the VM.
- **Self-hosted runners** — an agent process you install on your own hardware.
  Relevant when you need private network access, special hardware, or a
  genuinely persistent cache. Never attach one to a public repo without
  understanding that forks can then run arbitrary code on your machine.
- **OIDC deployment** — `id-token: write` plus a trust policy in your cloud
  provider, replacing stored credentials entirely.
- **Dependabot for actions** — a `.github/dependabot.yml` with the
  `github-actions` ecosystem opens PRs when your pinned action versions go stale.
  Worth adding on day one; the ecosystem moves fast.

### Reference pages worth bookmarking

- Workflow syntax reference — the exhaustive list of every key
- Contexts reference — every object and property available inside `${{ }}`
- `github.com/actions/runner-images` — exactly what is preinstalled on each
  runner image, and where breaking changes get announced first
- `github.com/actions` — the first-party actions, which cover most needs

### The habits that matter most

1. Quote your version strings. `3.10` is the float 3.1.
2. `fail-fast: false` on matrices, nearly always.
3. `if: always()` on summaries, cleanup, and aggregate gate jobs.
4. `concurrency` with `${{ github.ref }}` in the group, on every CI workflow.
5. Never interpolate `github.event.*` directly into a `run:` block.
6. Declare `permissions` explicitly; default to read, grant per job.
7. Pin third-party actions to a commit SHA if they touch secrets.
8. Treat caches as an optimization that is allowed to miss.
