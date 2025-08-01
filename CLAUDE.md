
### 🔄 Project Awareness & Context
- **Always read `qaai-legal-assistant-system.md`** at the start of a new conversation to understand QaAI’s architecture, goals, UI tokens, and constraints (DIFC-first, demo/free infra).
- **Check `TASK.md`** before starting work. If a task isn’t listed, add it with a short description and today’s date.
- **Use consistent naming & file structure** as defined in `qaai-legal-assistant-system.md`` (see the monorepo layout in `qaai-legal-assistant-system.md``).
- **Use `venv_linux`** (the virtual environment) for all Python commands, including tests and tooling.
- **Respect jurisdictional focus:** default to **DIFC** sources; treat outputs as **non‑legal advice**.
- Always review examples/design/README.md and the three *.profile.json files before UI work to ensure component styles follow the canonical tokens.

### 🧱 Code Structure & Modularity
- **Never create a file longer than 500 lines.** If approaching the limit, refactor into modules.
- Group by feature/responsibility. For **agents/graphs**:
  - `agents/graph.py` – LangGraph graph composition (nodes/edges/retries/routing).
  - `agents/nodes.py` – Node implementations (preflight/plan/retrieve/draft/verify/export).
  - `agents/prompts.py` – System prompts (DIFC-first), planner/drafter/verifier templates.
  - `agents/router.py` – Model selection (OpenAI/Anthropic) per step.
- Prefer **relative imports** within packages.
- **Use `python-dotenv` and `load_dotenv()`** for env vars in the API.

### 🧪 Testing & Reliability
- **Create Pytest unit tests** for new features (functions, classes, routes).  
- After updating logic, update tests accordingly.
- Tests live in `/apps/api/tests`, mirroring the main app structure. Include:
  - 1 expected‑use test
  - 1 edge case
  - 1 failure case
- Add a lightweight **E2E** test for SSE streams (Assistant), verifying that **thinking states** and **citations** arrive in order.
- **Use Puppeteer MCP for UI testing**: Before marking UI tasks complete, use `@puppeteer` to verify the web page renders correctly and matches design tokens.

### ✅ Task Completion
- **Mark completed tasks in `TASK.md`** immediately after finishing them.
- Add new sub‑tasks or TODOs discovered during work under “Discovered During Work” in `TASK.md`.

### 📎 Style & Conventions
- **Python** is the primary language for the backend; **TypeScript/React** for the frontend.
- Follow **PEP8**, use **type hints**, and format with **black**.
- Use **Pydantic** for request/response schemas; **FastAPI** for APIs.
- For data access, you may use **SQLModel** or **SQLAlchemy**; keep it small (SQLite by default).
- **Frontend** must consume **design tokens** from examples/design/ (Assistant/Vault/Workflow profiles). (the JSON profiles from this project). Don’t hard‑code colors or spacing.
- Write **docstrings** for every function using Google style:

  ```python
  def example(param1: str) -> str:
      """
      Brief summary.

      Args:
          param1 (str): Description.

      Returns:
          str: Description.
      """
Add # Reason: comments where logic is non-obvious (explain the why).

📚 Documentation & Explainability
Update README.md when features or setup steps change. **Use Context7 MCP** to verify documentation follows current best practices and includes up-to-date examples.

Comment non‑obvious code; write module-level docstrings explaining design choices (e.g., routing policy, DIFC filter logic). **Use Puppeteer MCP** to generate screenshots for documentation when visual examples would be helpful.

### 🔌 MCP Server Usage
- **Context7 MCP** - Use `@context7` to access the most updated developer documentation for libraries and frameworks. Always check for latest API changes, deprecated methods, and new features before implementing code.
- **Puppeteer MCP** - Use `@puppeteer` to view and test web pages during development. Essential for:
  - Testing UI components and responsive design
  - Verifying accessibility features work correctly  
  - Checking CSS styling matches design tokens
  - Taking screenshots for documentation
- **GitHub MCP** - Use `@github` for repository analysis, issue tracking, and code reviews
- **Filesystem MCP** - Use `@filesystem-desktop` to access project files, documents, and local resources

🧠 AI Behavior Rules
Never assume missing context. Ask questions if uncertain.

Do not hallucinate libraries/functions—use only verified packages (LangChain, LangGraph, FastAPI, FAISS, etc). **Use Context7 MCP** to verify current library versions and API documentation before implementing features.
Confirm file paths and module names before referencing them in code or tests. **Use GitHub MCP** to search the repository for existing implementations and patterns.
Never delete or overwrite existing code unless the task explicitly requires it (and is listed in TASK.md).
Citations are mandatory for legal answers. Prefer DIFC/DFSA sources and include section references when available.

🗂 Environment & Secrets
Use python-dotenv and .env loaded via load_dotenv() for local dev.
Never commit secrets; keep .env out of version control (use .env.example as a template).

🎨 UI Rules (Web)
Use React + Tailwind + shadcn/ui.
The single source of truth for UI style is the JSON in examples/design/ (Assistant/Vault/Workflow profiles). Do not hard‑code tokens. 
Implement SSE streaming for “thinking states.”
Ensure accessibility: keyboard nav, focus ring, and WCAG AA contrast.