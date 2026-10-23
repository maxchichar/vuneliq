# How we work on Vuneliq

These rules apply to everyone, including the repository owner and anyone using an AI coding assistant. Read this before changing the project. For responsibilities and the delivery plan, see [the team plan](docs/TEAM_ROLES_AND_MVP_DELIVERY.md).

## 1. The rule everyone must follow

**Nobody pushes directly to `main`. Always create a branch, make your changes there, and open a pull request.**

Think of `main` as the team's shared, reviewed copy. A branch is your work area. A pull request (PR) asks the team to check your changes before they join that shared copy. A merge adds approved changes to it.

This applies to small fixes, documentation, emergency fixes and the owner. Never force-push to `main`, delete it, or bypass its review rules. Urgent fixes use a small `fix/...` branch and the same review process.

## 2. Start with a clear task

Before coding, agree on:
- What problem are we solving?
- Who owns the task and who will review it?
- What must work before we call it finished?
- Does another task need to finish first?

Use one issue or agreed task per branch. Claim the task before starting so two people do not unknowingly build the same thing. Keep one active task at a time. If you are new, ask your mentor to help break it into a small first change.

## 3. Create your branch safely

These examples assume you already cloned the repository and your remote is called `origin`. Replace `yourname` and the example task with your own details.

First check for unfinished work:

```bash
git status
```

If you have changes, save them on their existing task branch before switching. If you are unsure, ask for help. Do not use destructive cleanup commands to make the warning disappear.

When your working folder is clean:

```bash
git switch main
git pull --ff-only origin main
git switch -c feat/yourname-cause-list
```

Branch names should explain the work:
- `feat/yourname-cause-list` — a new feature.
- `fix/yourname-donation-status` — a bug fix.
- `docs/yourname-setup-guide` — documentation.
- `test/yourname-checkout-flow` — tests.
- `chore/yourname-ci-setup` — maintenance.

If an instruction fails, stop and read the message. Ask your mentor instead of copying random commands. If your work must build on an unmerged branch, agree on that dependency with the owner first.

## 4. Make a small, understandable change

Keep each PR focused on one purpose. Avoid mixing a feature with unrelated formatting or cleanup. Use clear names and explain unusual decisions briefly in comments.

Follow the agreed stack and existing project patterns. Do not change the framework, database, authentication method, hosting service or add a major dependency without discussing the need with the technical owner. For the four-day MVP, finish the agreed primary journey before adding extra features.

For our modular monolith: each part of the backend has its own responsibility, but they live in one application. Use another module's agreed service functions; do not change its database tables behind its owner's back. Share API changes with the frontend owner before merging them. Regenerate the TypeScript API client when the API contract changes; do not hand-edit generated code.

## 5. Check your work before sharing it

Run the relevant checks documented in the repository. As the project is built, maintainers must add the exact commands to the setup guide. Never claim a check passed if you did not run it.

- Backend change: check the affected behavior with pytest; include invalid input and access-denied cases when relevant.
- Frontend change: check types/build and relevant Vitest behavior; inspect loading, empty, error and success states.
- A full user journey: check it in the browser and add or update an appropriate Playwright test.
- Database change: have the backend lead review the Alembic migration and verify it on a disposable database.
- Documentation change: check that instructions and links are accurate; no application test is needed for prose alone.

Use fake or sandbox data. Never experiment with real donor data or live money. Include a useful failure case, not just a successful click. Describe any check you could not run and why.

## 6. Save your work and push only your branch

Check that you are on your task branch:

```bash
git branch --show-current
git diff
git status
```

Stage only the files you intend to include. This example saves a documentation change; replace the path for your task:

```bash
git add CONTRIBUTING.md
git diff --cached
git commit -m "docs: explain team contribution rules"
git push -u origin HEAD
```

**Do not run that push while on `main`.** Check the branch name first. Inspect the staged changes for passwords, keys and unrelated files before committing.

Do not rewrite a branch someone else is using. Never force-push a shared branch. If a private task branch needs its history rewritten, coordinate with the reviewer and use a safe, agreed procedure.

## 7. Open a pull request early

On GitHub, open a PR from your task branch into `main`. Use a draft PR while the work is unfinished. Request review when it is ready.

Use a clear title, such as “Show donation status after checkout”. Include:
- **Problem:** what was missing or broken?
- **Change:** what does the user experience now?
- **Task:** link the issue or agreed task.
- **Checks:** what did you test, and what were the results?
- **Evidence:** screenshots for visible UI changes or useful test results.
- **Risks:** database/API changes, new settings, known limitations and recovery steps, when relevant.

Never hide unfinished work. State what is still pending. Do not include credentials, private donor details or sensitive screenshots.

## 8. Review, approve and merge

Every PR needs at least one approval from a teammate other than its author. Request the reviewer responsible for that area. Security-sensitive changes need the security owner's review; database changes need the backend lead's review. If someone is unavailable, the repository owner names a suitable replacement.

Reviewers check that the change solves the task, is understandable, handles likely failures, protects user data and has appropriate evidence. Explain requested changes kindly and specifically. Authors respond to each review point and request another review after fixing it.

Before merging:
- The work meets its agreed completion criteria.
- Required checks pass; reviewers know about any unavailable checks.
- Relevant review conversations are resolved.
- Changes made after approval have been reviewed if they affect behavior or risk.
- Merge conflicts are resolved and affected checks are rerun.

Only the repository owner or a designated maintainer merges approved PRs. Do not approve your own work, bypass a failed check, or merge merely because the deadline is close. If nobody else can review the owner's change, it waits for an independent review.

After merge, update your local `main` and start the next task from a fresh branch. Delete the completed remote task branch only when no one else depends on it.

## 9. Protect people, money and secrets

Never commit passwords, API keys, access tokens, real `.env` values, database exports or private user information. Use environment variables and an example configuration with placeholders. Keep provider keys on the backend.

If a secret is exposed, tell the owner privately immediately and revoke or rotate it. Deleting the line from the latest file does not remove it from Git history.

Check permissions on the server: hiding a button does not stop someone from requesting another user's data. Validate input and limit expensive requests. Do not log sensitive payloads or payment details.

For donation features:
- Use provider-hosted checkout and sandbox payments during development.
- Never store raw card details.
- Verify provider messages before confirming payment.
- Receiving the same payment message twice must not count the donation twice.
- A successful browser redirect is not proof that money was received.

AI output must be checked, clearly presented and grounded in available sources. AI must not invent donation impact or confirm payment. If you use an AI coding assistant, review its changes yourself and follow the same branch, review and testing rules.

Report security problems privately to the owner. Do not publish exploit details or secrets in public issues.

## 10. Work together without blocking each other

Post a brief update at the agreed daily check-in: what you finished, what you are doing next and what is blocking you. If you have been stuck for about 30 minutes, ask for help with the error, steps tried and the result you expected. Remove secrets from any shared output.

Tell the affected owner before changing a shared API, database shape or configuration. Record important decisions in the team documentation so absent teammates can catch up.

When your branch falls behind, save your changes first, then bring in the latest shared work:

```bash
git fetch origin
git merge origin/main
```

If Git reports a conflict, it means two changes overlap. Resolve it with the other author or mentor, inspect the final result and rerun relevant checks. Never choose one side blindly or delete another person's work just to make the conflict disappear.

Be respectful. Review the work, not the person. Beginners should ask questions early; experienced teammates should explain the reason behind corrections.

## 11. What “done” means

A task is done when the feature works in the agreed environment, likely failure cases are handled, relevant checks pass, documentation is updated where needed, another person has reviewed it, and the approved PR has been merged. “It works on my laptop” or “I pushed my branch” is a progress update, not completion.

Before a release, verify the whole primary journey on the deployed version, record known limitations and confirm a recovery plan. A merge does not automatically authorize a production release; the owner coordinates release readiness with QA and security.

## 12. Make the main-branch rule enforceable

This file states team policy. **A Markdown file cannot itself block a push.** The repository owner must configure GitHub branch protection or a ruleset targeting `main`.

Owner setup checklist:
- Require a pull request before merging and at least one independent approval.
- Require approval again after meaningful new changes, and resolve review conversations before merge.
- Require the real CI checks once they exist; do not enter invented check names.
- Block force-pushes and deletion of `main`.
- Apply protections to administrators too; avoid routine bypass access.
- Verify using a non-owner collaborator that direct pushes are rejected and the normal PR process still works.

Protection settings have not been configured or verified by adding this document. Until verified, everyone must still follow the policy.

**Our shared promise: branch first, review together, test what matters, and keep `main` ready for the team.**
