---
description: Workflow for committing and pushing changes to GitHub
---

# Auto Git Push Workflow

After completing any code changes, the agent should automatically stage, commit, and push to GitHub.

## Steps

// turbo-all

1. Stage all changes:
```bash
git add -A
```

2. Commit the changes with a descriptive message:
```bash
git commit -m "YOUR_COMMIT_MESSAGE"
```
Replace `YOUR_COMMIT_MESSAGE` with a brief, descriptive summary of the changes made.

3. Push to GitHub:
```bash
git push
```

## Notes

- Always use descriptive commit messages that explain what was changed
- If there are no changes to commit, skip this workflow
- Run these commands from the project root directory: `e:\femboibot`
