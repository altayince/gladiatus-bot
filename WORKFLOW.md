# GLA Workflow

This repository uses an issue-first, branch-per-task, PR-only flow.

## Rules
- Start every task with a GitHub issue.
- Assign every issue to `@me` so ownership stays with you.
- Name branches with the GLA ticket number:
  - `feature/GLA-[ticket]-description`
  - `bugfix/GLA-[ticket]-description`
- Before creating a new feature or bugfix branch, checkout `main` and pull the latest changes, then branch from that updated state.
- Do all development on the task branch.
- Open a PR into `main`.
- Assign the PR to `@me` and add it to the `GLA` project.
- Review the PR yourself, then merge once checks pass.
- Required review approval is disabled because this is a single-person project.
- If the PR is merged, the linked GLA issue closes automatically.
- If the PR is closed without merge or deleted, the linked issue stays open.
- Do not push directly to `main`.
- After each feature or bugfix, update the GUI's `Neler degisti?` panel with a short summary of what changed.
- Format each new note with the issue number and issue title, then the short summary.
- Keep the newest update at the top and preserve only the latest 10 entries.

## Enforced Controls
- GitHub branch protection blocks direct pushes to `main`.
- A local `pre-push` hook blocks direct pushes to `main` and rejects non-GLA branch names.
- A PR policy workflow checks branch naming and verifies that the ticketed GitHub issue exists.

## Recommended Flow
1. Create the issue in GitHub, assign it to yourself, and note the issue number.
2. Checkout `main` and pull the latest changes.
3. Create a branch from the updated `main` using the issue number.
4. Install local hooks once per clone.
5. Implement the change on the task branch.
6. Update the GUI change-notes panel with the issue number, issue title, and a short summary of the work.
7. Push the branch and open a PR.
8. Wait for review and approval.

## Branch Naming Examples
- `feature/GLA-2-workflow-enforcement`
- `bugfix/GLA-12-login-fix`

## Local Hook Setup
Run this once after cloning:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install-githooks.ps1
```
