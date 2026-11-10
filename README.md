# 5_algorithms — Numerical Equation Solver

A Numerical Methods (Math 3) project: solve `f(x) = 0` with classical root-finding
algorithms and solve linear systems `Ax = b` with the Gauss methods. Includes a
bonus web UI (Next.js) that talks to a Python FastAPI backend.

## Features

- Enter any equation in `x` — powers with `^`, functions like `sin`, `cos`, `exp`, `log`.
  Unicode lookalikes (pasted minus signs, `x²`-style superscripts, `×`, `÷`) are normalized automatically.
- Pick a method from a dropdown; the required fields change with it.
- The Gauss methods accept a linear system typed as matrix rows in a text area.
- Client-side validation before the request is sent (interval order, positive
  tolerance, positive integer max iterations, square system, etc.).
- Result card: approximate root / solution vector, number of iterations
  (or operations), final error, method used.
- Collapsible steps table with one row per iteration (columns depend on the method).
- An SVG plot of `f(x)` with the root marked (root-finding methods only).
- Backend error messages are surfaced in a red error box.
- Responsive layout (single column on mobile) with automatic dark mode.

## The five methods

| Display name            | Required fields                              | Value sent to the API |
| ----------------------- | -------------------------------------------- | --------------------- |
| Bisection Method        | interval start `a`, end `b`                  | `bisection`           |
| Gauss Elimination       | system `Ax = b` (matrix rows)                | `gauss_elimination`   |
| Gauss-Seidel            | system `Ax = b` + tolerance + max iterations | `gauss_seidel`        |
| Secant Method           | first guess `x0`, second `x1`                | `secant`              |
| Modified Secant Method  | initial guess `x0`, perturbation delta       | `modified_secant`     |


Convergence criteria: `|x_new − x_old| < tolerance` (or `|f(x)| < tolerance`)
within `max_iterations`; otherwise the backend answers with
`"Tolerance was not reached within the maximum number of iterations"`.

## Project structure

```
5_algorithms/
├── package.json          # root scripts: npm run start runs BOTH servers
├── README.md
├── .gitignore
├── backend/              # FastAPI (Python 3.13 venv in backend/.venv)
│   ├── main.py           # POST /api/solve + all five methods
│   ├── requirements.txt  # fastapi, uvicorn[standard]
│   └── .venv/            # gitignored virtual environment
└── frontend/             # Next.js 16 (App Router, TypeScript, Turbopack)
    ├── app/
    │   ├── layout.tsx    # Inter font, metadata, LTR
    │   ├── page.tsx      # the solver UI ("use client")
    │   ├── page.module.css
    │   └── globals.css
    └── next.config.ts    # turbopack root fix for the monorepo layout
```

## Getting started

Prerequisites: **Node.js 20.9+** and **Python 3.10+** on the PATH.

```bash
# 1. one-time setup (installs npm deps, creates the Python venv, installs pip deps)
npm run setup

# 2. start both servers
npm run start
```

| URL                                | What it is                    |
| ---------------------------------- | ----------------------------- |
| http://localhost:3000              | Web UI (Next.js)              |
| http://localhost:8000              | Backend API (FastAPI)         |
| http://localhost:8000/docs         | Interactive API documentation |

## The API

### `POST /api/solve`

Request (root-finding method):

```json
{
  "method": "bisection",
  "equation": "x^3 - x - 2",
  "params": { "a": 1, "b": 2, "tolerance": 0.0001, "max_iterations": 50 }
}
```

Request (linear system):

```json
{
  "method": "gauss_seidel",
  "system": [[4, 3, 0, 120], [3, 4, -1, 127.4], [0, -1, 4, 91.5]],
  "params": { "tolerance": 0.0001, "max_iterations": 50 }
}
```

Params are method-dependent: `a`, `b` for Bisection; `x0`, `x1` for Secant;
`x0` and `delta` (default `0.01`) for Modified Secant; `tolerance`
(default `0.0001`) and `max_iterations` (default `50`) where applicable.

Success response:

```json
{
  "method": "bisection",
  "equation": "x^3 - x - 2",
  "root": 1.5213797,
  "iterations": 14,
  "error": 0.00006103515625,
  "converged": true,
  "steps": [
    { "i": 1, "a": 1.0, "b": 2.0, "c": 1.5, "fc": -0.125, "error": 0.5 },
    ...
  ],
  "graph": { "root": 1.5213797, "points": [[0.9, -1.271], [0.91, -1.256], ...] }
}
```

For the Gauss methods the response has `solution` (the x vector) instead of
`root`, and no `graph`.

Step column keys by method:

- Bisection: `i, a, b, c, fc, error`
- Secant: `i, xnm1, xn, xnp1, fxn, error`
- Modified Secant: `i, xn, fxn, f2, error`
- Gauss Elimination: `i, op, v0..` (row operation + the resulting row values, the last value is `b`)
- Gauss-Seidel: `i, v0.., error` (`v0..v{n-1}` are `x1..xn`)

Failure (HTTP 400):

```json
{ "detail": { "message": "No root exists in the given interval (f(a) and f(b) have the same sign)" } }
```

The UI shows the `message` from the backend in a red box. Server messages include:

- `No root exists in the given interval (f(a) and f(b) have the same sign)`
- `Invalid equation: ...`
- `The matrix is singular, Gauss Elimination cannot solve this system`
- `A zero element on the diagonal, Gauss-Seidel cannot solve this system`
- `Tolerance was not reached within the maximum number of iterations`
- divergence / zero-denominator messages for Secant and Modified Secant

If the request never reaches the server (network error), the UI shows
*"Could not reach the server, please try again"*.

Example with curl:

```bash
curl -X POST http://localhost:8000/api/solve \
  -H "Content-Type: application/json" \
  -d '{"method": "modified_secant", "equation": "x^3 - x - 2", "params": {"x0": 1.5, "delta": 0.01}}'
```

### Supported equation syntax

The backend parses the equation with Python's `ast` module (never `eval`),
so only a safe subset is allowed:

- variable `x`, constants `pi`, `e`, `tau`
- operators `+ - * / ^ %` (`^` is treated as a power, `**`)
- functions `sin cos tan asin acos atan sinh cosh tanh exp log ln sqrt abs pow`
- integer/decimal numeric literals

Examples: `x^3 - x - 2`, `x - cos(x)`, `exp(x) - 3`, `x^2 - 4*sin(x)`.

## How the iterations are computed

- **Bisection**: repeatedly bisect `[a, b]`, keep the half where the sign of
  `f` changes. Error per row is `|b − a| / 2`.
- **Gauss Elimination**: forward elimination with partial pivoting
  (row swaps keep pivots nonzero); rows are recorded in the steps table after
  every operation (`R3 -> R3 − 2R1` etc.), then back substitution.
- **Gauss-Seidel**: `x_i ← (b_i − Σ_{j≠i} A[i][j]·x_j) / A[i][i]`, using updated
  values immediately; stops when the max change is below the tolerance.
- **Secant**: `x_{k+1} = x_k − f(x_k)·(x_k − x_{k-1}) / (f(x_k) − f(x_{k-1}))`.
- **Modified Secant**: `x_{k+1} = x_k − δ·x_k·f(x_k) / (f(x_k + δ·x_k) − f(x_k))`
  with δ (default `0.01`) from the Delta field.

## Tech stack

- **Frontend:** Next.js 16 (App Router), React 19, TypeScript, CSS Modules,
  Inter via `next/font/google`, no extra chart library (the plot is plain SVG).
- **Backend:** FastAPI + uvicorn, Pydantic models for request validation,
  CORS middleware so the dev server on port 3000 can call the API on port 8000.
- **Root orchestration:** `concurrently` runs both dev servers with
  `npm run start`.

## Git

```bash
# repository: https://github.com/mostafaelgndy-ai/5_algorithms
git add .
git commit -m "Add solver UI, /api/solve endpoint and README"
git push origin master
```
