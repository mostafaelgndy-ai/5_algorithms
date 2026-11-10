# 5_algorithms — Numerical Equation Solver

A Numerical Methods (Math 3) project: solve `f(x) = 0` using five classical
root-finding algorithms. Includes a bonus web UI (Next.js) that talks to a
Python FastAPI backend.

> **Note:** the five algorithms were not named in the instructor's message.
> The four implemented here (Bisection, False Position, Newton-Raphson, Secant)
> are the common course methods; **Fixed Point** is a placeholder implementation
> (`x_{k+1} = x_k − f(x_k)`) and should be adjusted to match the course.

---

## Features

- Enter any equation in `x` — powers with `^`, functions like `sin`, `cos`, `exp`, `log`.
- Pick a method from a dropdown; the required numeric fields change with it.
- Client-side validation before the request is sent (interval order, positive
  tolerance, positive integer max iterations, etc.).
- Result card: approximate root, number of iterations, final error, method used.
- Collapsible steps table with one row per iteration (columns depend on the method).
- An SVG plot of `f(x)` with the root marked.
- Backend error messages are surfaced in a red error box.
- Responsive layout (single column on mobile) with automatic dark mode.

## The five methods

| Display name     | Required fields               | Value sent to the API |
| ---------------- | ----------------------------- | --------------------- |
| Bisection        | interval start `a`, end `b`   | `bisection`           |
| False Position   | interval start `a`, end `b`   | `false_position`      |
| Newton-Raphson   | initial guess `x0`            | `newton`              |
| Secant           | first guess `x0`, second `x1` | `secant`              |
| Fixed Point      | initial guess `x0`            | `fixed_point`         |

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

Request:

```json
{
  "method": "bisection",
  "equation": "x^3 - x - 2",
  "params": { "a": 1, "b": 2, "tolerance": 0.0001, "max_iterations": 50 }
}
```

Params are method-dependent: `a`, `b` for Bisection / False Position; `x0` for
Newton-Raphson / Fixed Point; `x0` and `x1` for Secant; `tolerance`
(default `0.0001`) and `max_iterations` (default `50`) always apply.

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

Step column keys by method:

- Bisection / False Position: `i, a, b, c, fc, error`
- Newton-Raphson: `i, xn, fxn, dfxn, error`
- Secant: `i, xnm1, xn, xnp1, fxn, error`
- Fixed Point: `i, xn, xnext, fxn, error`

Failure (HTTP 400):

```json
{ "detail": { "message": "No root exists in the given interval (f(a) and f(b) have the same sign)" } }
```

The UI shows the `message` from the backend in a red box. Server messages include:

- `No root exists in the given interval (f(a) and f(b) have the same sign)`
- `Invalid equation: ...`
- `The derivative equals zero`
- `Tolerance was not reached within the maximum number of iterations`
- divergence messages for Newton-Raphson, Secant, and Fixed Point

If the request never reaches the server (network error), the UI shows
*"Could not reach the server, please try again"*.

Example with curl:

```bash
curl -X POST http://localhost:8000/api/solve \
  -H "Content-Type: application/json" \
  -d '{"method": "newton", "equation": "x^3 - x - 2", "params": {"x0": 1.5}}'
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
- **False Position (Regula Falsi)**: like Bisection but interpolates a
  straight line between `(a, f(a))` and `(b, f(b))` and uses its root.
- **Newton-Raphson**: `x_{k+1} = x_k − f(x_k)/f'(x_k)`. The derivative is
  computed numerically (central finite difference).
- **Secant**: `x_{k+1} = x_k − f(x_k)·(x_k − x_{k-1}) / (f(x_k) − f(x_{k-1}))`.
- **Fixed Point (placeholder)**: `x_{k+1} = x_k − f(x_k)`, i.e. iterating
  `g(x) = x − f(x)`; adjust if the course defines `g(x)` differently.

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
