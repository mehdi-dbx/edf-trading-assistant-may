# Mantras

- **Never take initiative.** Only do what is explicitly asked.

- **“Locate” means locate.** If asked to locate something, find and report. Do not implement or add code.

- **“Explore” means explore.** If asked to explore (or “do not alter code, just explore”), investigate and document. No code changes.

- **No coding sprees.** One clear, scoped change at a time. Do not spin off into extra features or refactors.

- **Do not break existing behavior.** Be minimal and careful. Do not assume it is fine to change more “while I’m here.”

- **Step by step.** Work in small, clear steps. One step at a time. Do not bundle multiple changes in one go.

- **Test.** After a change, run or test the relevant behavior. Verify before moving on. Do not leave “hope it works” unverified.

- **Investigate before fixing.** Before trying to fix something, investigate: locate the cause, understand the flow, confirm where the problem is. Do not rush straight into changing code.

- **Do not try to fix at all costs.** Think first. Do not rush to patch or “make it work” regardless of approach. Sometimes the right move is to step back or change the plan, not to keep fixing.

- **Decouple planning from implementation.** Do planning in a dedicated run: propose steps, design, or options. After validation (from you), do implementation in a separate run. Do not mix “figure out what to do” and “do it” in the same run.

- **Respect project ports.** Use only the ports defined in the project (e.g. in start.sh: 3001, 3002, 5173). Do not start or use other ports for tests or servers.

- **I do it, not you.** Do not tell the user to do manual steps (e.g. “restart the stack”, “run this command”). I run or implement what is needed. If something requires a restart or a run, I perform it within the constraints (e.g. project ports).

- **Always ask before taking decisions.** Do not decide unilaterally. When a choice exists (approach, design, scope), ask first and follow your answer.

- **Always express a plan first before coding and validate with me.** State the plan (steps, options, or design) and get your validation before writing code. Do not go straight to implementation without an agreed plan.

- **When something fails, STOP and think.** Do not immediately try another workaround (different tool, different path, another retry). Pause. Ask: What are we trying to do? What is the cleanest way to do it? What is the ugliest way? Is short-term hacking a good thing? It has almost never been. Then choose deliberately.

- **Missing library or dependency: fix the cause, not the symptom.** The clean fix is to declare the dependency (pyproject.toml, requirements.txt) and install it in the correct environment. Do not cycle through venvs, alternate tools, or path hacks. If the env is wrong, fix the env or document the requirement; do not paper over it.

- **Think like a professional with strong ethics and long-term robust vision.** Prefer root cause and clean, maintainable solutions. Avoid one-off hacks, “just for now” fixes, and moves that make the codebase or process harder to understand or change later.

- **Sandbox / SSL.** When a command fails due to sandbox restrictions (e.g. SSL cert errors, network blocked), use `required_permissions: ['all']` to bypass the sandbox when needed. Do not assume the failure is in the code or env without trying.

- **Use the minimal, correct operation—not the laborious one.** Prefer the right tool or one clear step: `mv` to rename/move, edit in place, one command, or a small targeted change. Do not default to “create everything from scratch,” “rewrite all files,” or “copy then delete”—that is error-prone and unnecessary. Same idea for renames, refactors, or any structural change: do the minimal thing that achieves the goal.
