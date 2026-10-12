# Workspace Guidelines: InsightOrbit Automation

## Workflow Rules for Every Task
When executing any task or feature request in this project, you MUST strictly follow this workflow:

1. **Understand & Analyze**:
   - Before writing any code, ALWAYS read `README.md` first to understand the current system functionality, existing architecture, and how the user's request fits into the current logic.
   
2. **Plan & Validate**:
   - Provide the user with a clear, step-by-step implementation architecture for their request.
   - Design and propose rigorous functional validation procedures (e.g. how the changes will be tested and verified against the existing modules like `main.py` or `run_news.py`).

3. **Documentation & Version Control**:
   - Once a task is completely implemented and tested, you MUST update `README.md` (specifically the Changelog section) with a description of the latest changes.
   - Run `git add`, `git commit`, and `git push` to synchronize the changes to the GitHub repository automatically.
