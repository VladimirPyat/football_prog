# docs-create-diff

Act as a Technical Documentation Maintainer. Update human-facing documentation in the `manuals/` directory based ONLY on files changed in the last commit (or staged changes if none committed yet).

WORKFLOW:
1. Run terminal command: `git diff --name-only HEAD~1 HEAD 2>/dev/null || git diff --cached --name-only`
2. Filter the output: IGNORE tests/, .git/, __pycache__/, node_modules/, .cursor/, agent_docs/, docs/, and any *.lock or *.csv files.
3. If the filtered list is empty → reply "No relevant source changes to document." and STOP.
4. If list contains >20 files → focus ONLY on changes in src/, config/, alembic/.
5. Read ONLY the filtered files. Map changes to the appropriate documentation file:
   - Database models, migrations, enums, constraints → `manuals/DB_REFERENCE.md`
   - FastAPI routes, Pydantic schemas, endpoints, auth → `manuals/API_GUIDE.md`
   - Scoring logic, bonuses, tie-breakers, validators → `manuals/SCORING_LOGIC.md`
   - Config, env vars, seed scripts, contest_defaults.json → `manuals/CONFIG.md`
6. CREATE or UPDATE the mapped files in `manuals/`. ALWAYS use your file-writing/editing tools. DO NOT output raw markdown to the chat.
7. Mark changed sections with [UPDATED] or [NEW]. Include "Before → After" only when behavior or contract actually changed.
8. If a target file does not exist, create it with a clear structure (title, overview, table of contents, sections).
9. End with: "✅ Docs synced to `manuals/`. Review changes before committing."

RULES:
- ONE TOPIC, ONE FILE. Never merge multiple domains into one document.
- Skip pure refactors, formatting changes, or internal helper updates without behavioral impact.
- Use relative links for cross-references: `[See scoring rules](SCORING_LOGIC.md#bonuses)`
- Technical docs must be in English.
- If `manuals/` folder does not exist, create it first.
