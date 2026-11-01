---
name: auto-git-push
description: >-
  Automatically updates README.md changelog, commits with conventional commit message,
  and pushes changes to the remote GitHub repository whenever any modification or task is completed.
---

# Auto Git Push & Changelog Sync Workflow

This skill defines the standardized workflow for updating documentation and pushing modifications to the remote GitHub repository (`YaodeChiang4181/Post-auto-generator`) automatically.

## Activation Triggers
Trigger this skill whenever:
- A code change, bugfix, or new feature implementation has completed its verification.
- Files have been added, modified, or removed in the workspace.
- The user requests to sync, commit, or push changes.

## Step-by-Step Procedure

### 1. Run Functional & Regression Tests
Before committing, always ensure that test suites pass:
```powershell
python -m unittest discover -s . -p "test_*.py"
```
If any test fails, fix the issue before proceeding to the git workflow.

### 2. Update Documentation (`README.md`)
Open `README.md` and prepend the latest changes under the `## 更新日誌 (Changelog)` section:
- Include a descriptive Chinese title summarizing the main improvement.
- Use structured bullet points detailing what changed, why it changed, and which files/modules were affected.

### 3. Check Working Tree Status
Inspect changed, untracked, and deleted files:
```powershell
git status
```

### 4. Stage and Commit
Stage all changes and commit using a concise Conventional Commits message (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`):
```powershell
git add -A
git commit -m "<type>(<scope>): <concise descriptive message>"
```

### 5. Push to Remote Repository
Push commits directly to `origin main`:
```powershell
git push origin main
```

### 6. Verification
Verify that the remote repository is in sync:
```powershell
git status
```
Ensure it shows `Your branch is up to date with 'origin/main'` and `nothing to commit, working tree clean`.
