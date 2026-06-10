# GUI Manual Test Checklist — Plugin & Function-Creation Flow

Manual tests for things that can't be checked automatically: the real browser UI,
the full **create → export → restart → run** loop, and error/corner cases.

These focus on the `plugin-refactoring` work (typed-`env` scaffold, plugin
dropdown, auto-discovery, manifest, collision guard, engine dup-name fixes), plus
general "can I build anything without breaking" sanity.

**How to mark:** put `[x]` for pass, `[!]` + a note for anything off.

> **Tip:** keep the backend terminal visible while testing — collisions, warnings,
> and scaffold errors print there. A red `[ERROR]` line in the GUI log is the
> stderr channel, not necessarily a failure; trust the process exit code and
> explicit messages.

---

## 0. Setup & smoke

- [x] `./run.sh` starts both Flask (:5001) and Vite (:3000) with no traceback.
- [x] Open http://localhost:3000 — the app loads, no blank screen, no red errors
      in the browser console (F12).
- [x] In a terminal: `curl -s http://localhost:5001/api/health` → `"status": "healthy"`.
- [x] `curl -s http://localhost:5001/api/plugins` → lists `MicroC`, `PhysiBoSS`,
      `Test_GUI`, `common`, each with a `manifest` and `version`.

---

## 1. New Function dialog (the rewritten UI)

Open a **behaviour or init canvas** first (the dialog is gated to those).

- [ ] **Gating:** on a non-behaviour canvas (e.g. scheduler), the **New Function**
      button is disabled with a tooltip explaining why.
- [ ] On a behaviour canvas, **Library → New Function** opens the dialog.
- [ ] **Plugin dropdown** is populated from the backend (MicroC / PhysiBoSS /
      Test_GUI — `common` should **not** appear) and ends with **➕ New plugin…**.
- [ ] **Stage** defaults sensibly from the canvas you're on.
- [ ] **Derived path** preview updates live as you type the name / change stage /
      change plugin — e.g. `opencellcomms_adapters/MicroC/functions/intracellular/my_fn.py`.
      You can **not** type a raw path anywhere (this is intentional).
- [ ] Choose **➕ New plugin…** → a text box appears for the plugin name, and an
      **Existing** button returns to the dropdown. The derived path uses the new name.
- [ ] **Capability checkboxes** (population / simulator / gene networks) toggle.
- [ ] Tick **"This is a setup function"** → the capability checkboxes disappear.
- [ ] **Add Parameter** with each type (INT/FLOAT/BOOL/STRING/DICT): BOOL shows a
      true/false dropdown, DICT shows a disabled `{}`, others a default field.
- [ ] **Validation messages** (the amber line) appear and block submit for:
      empty name; name with spaces/`-`; no plugin chosen; new-plugin name with
      spaces/`-`; a parameter with no name or an invalid name.
- [ ] **Add to Project** with valid input → dialog closes, the function appears in
      the Library marked unsaved (✱) and is draggable onto the canvas.

---

## 2. Export & persistence (the core bug we fixed)

This is the most important suite — functions used to vanish on restart.

- [ ] Create a function in an **existing** plugin (e.g. MicroC), drag it onto the
      canvas, click **Export Behavior**.
- [ ] Confirm on disk: the `.py` appears under
      `opencellcomms_adapters/MicroC/functions/<stage>/`, and the import line was
      added to `opencellcomms_adapters/MicroC/register.py`.
- [ ] Create a function in a **brand-new plugin** (➕ New plugin… → e.g. `my_test`),
      export it. Confirm on disk the whole package was scaffolded:
      `my_test/__init__.py`, `register.py`, `plugin.toml`,
      `functions/<stage>/<fn>.py`, and the intermediate `__init__.py` files.
- [ ] **No `register.py.bak`** is left next to a brand-new `register.py`.
- [ ] **`curl /api/plugins`** now lists `my_test`.
- [ ] **RESTART the backend** (Ctrl+C, `./run.sh`). Reopen the GUI.
      → the new function and `my_test` plugin are **still present** in the
      registry / palette. *(This is the bug that's fixed — verify carefully.)*
- [ ] Re-export the same behaviour (no new functions): it writes the
      `.subworkflow.json` and reports "no new .py files" rather than duplicating.

---

## 3. Generated code quality

Open each generated file (GUI code viewer, or on disk).

- [ ] A normal function has `def <fn>(env: BiologicalContext, ...)`, a
      `compatible_kernels=["biophysics"]`, and `requires=[...]` matching the
      capability checkboxes you ticked.
- [ ] The file imports `from src.biology.context import BiologicalContext`.
- [ ] A **setup function** (exempt) instead has `context: Dict[str, Any] = None`
      and `typed_env_exempt=True`, with the `if not context:` guard.
- [ ] The `category=` in the decorator matches the **Stage** you picked (not just
      the folder name).
- [ ] Declared parameters appear both in the decorator `parameters=[...]` and in
      the function signature with the right Python types/defaults.

---

## 4. Plugin system — manifest, listing, collisions

- [ ] Edit a `plugin.toml` (e.g. bump `version` to `0.2.0`), restart backend,
      reopen the dialog → the dropdown label shows the new version.
- [ ] **Collision (hard error):** create a function whose name **already exists**
      in another plugin (e.g. name it `update_metabolism`, which `common` defines),
      export it. → expect a **failure**: the scaffold/registry refuses with a
      "DUPLICATE FUNCTION NAME" error in the backend terminal, and the GUI surfaces
      an error rather than silently overwriting. *(Then delete the bad file.)*
- [ ] **Same-name re-export is fine:** export the *same* function twice (no rename)
      → no collision error (re-running the decorator on the same file is allowed).
- [ ] A folder that is **not** a valid plugin (no `register.py`) does **not** appear
      in `/api/plugins` and does not break startup.

---

## 5. End-to-end simulation (does the built thing actually run?)

- [ ] Build a small workflow that includes one function you created (give it real
      logic, e.g. mark cells necrotic below an oxygen threshold), wire it into the
      right stage, and **Run** the simulation.
- [ ] The run completes (exit `[COMPLETE]`), and your function's `print(...)` line
      shows in the log — i.e. it was actually called.
- [ ] A function that declares `requires=["population"]` but runs under a kernel
      that doesn't provide it **fails loudly** at load (expected) rather than
      silently doing nothing.
- [ ] Results/plots appear in the Results tab.

---

## 6. Regression — don't break what already worked

- [ ] Existing workflows (e.g. a MicroC workflow) still **load** and **run**.
- [ ] The function palette still lists the built-in engine + adapter functions
      (~130 functions); nothing obviously missing.
- [ ] **Engine dup-name fix:** the palette shows both **"Save Checkpoint (CSV
      Format)"** (`save_checkpoint`) and **"Save Checkpoint (VTK)"**
      (`save_checkpoint_vtk`) as distinct entries, and **"Print Simulation
      Summary"** appears exactly **once**.
- [ ] Save a workflow JSON that has staged (unsaved ✱) user functions, reload it
      → the staged functions are still listed (they round-trip through the JSON).
- [ ] Dict/list parameters on a node render as an **editable table**, not a flat
      unreadable string, in the Parameter editor.

---

## 7. Corner cases & error handling

- [ ] **Backend down when the dialog opens:** stop Flask, open New Function → the
      plugin dropdown degrades gracefully (loading/empty state, no crash). Restart
      Flask and it recovers.
- [ ] **Two functions, one new plugin:** create two functions in the same new
      plugin before exporting → both land in the same `register.py`, both load.
- [ ] **Stage vs canvas mismatch:** on an *Intercellular* canvas, create a function
      but pick stage *Initialization* → the generated `category` is
      `INITIALIZATION` (the explicit choice wins).
- [ ] **DICT parameter:** a function with a DICT parameter exports with `default={}`
      and (in a workflow) renders as an editable table, per the GUI-readability rule.
- [ ] **Cancel / discard:** open the dialog, fill it in, **Cancel** → nothing is
      staged or written. Stage a function, then remove it from the Library before
      exporting → no file is written.
- [ ] **Duplicate staged name:** try to create two staged functions with the same
      name → the second is rejected/ignored (no silent duplicate).
- [ ] **Weird but valid names:** a function name with trailing/leading spaces is
      trimmed; a plugin name like `My_Plugin2` is accepted; `2plugin` or `my-plugin`
      is rejected by validation.
- [ ] **Special characters in parameter default** (e.g. a STRING default with a
      quote) exports to syntactically valid Python (no scaffold syntax error).

---

## 8. Sign-off

- [ ] All of §2 (persistence) and §5 (end-to-end run) pass — these are the
      load-bearing ones.
- [ ] No collision warnings on a clean backend start (`save_checkpoint` /
      `print_simulation_summary` are resolved).
- [ ] Note any `[!]` items above with a short repro so they can be triaged.
