"use client";

import { useState } from "react";
import styles from "./page.module.css";

type Method = "bisection" | "gauss_jacobi" | "gauss_seidel" | "secant" | "modified_secant";

const METHODS: { value: Method; label: string }[] = [
  { value: "bisection", label: "Bisection Method" },
  { value: "gauss_jacobi", label: "Gauss-Jacobi Iteration" },
  { value: "gauss_seidel", label: "Gauss-Seidel Iteration" },
  { value: "secant", label: "Secant Method" },
  { value: "modified_secant", label: "Modified Secant Method" },
];

type Step = Record<string, number | string>;

type Column = { key: string; label: string; text?: boolean };

type GraphData = { root: number; points: number[][] };

type SolveResult = {
  method: Method;
  equation: string | null;
  root: number | null;
  solution: number[] | null;
  iterations: number;
  error: number;
  steps: Step[];
  graph: GraphData | null;
};

const SCALAR_COLUMNS: Partial<Record<Method, Column[]>> = {
  bisection: [
    { key: "i", label: "i" },
    { key: "a", label: "a" },
    { key: "b", label: "b" },
    { key: "c", label: "c" },
    { key: "fc", label: "f(c)" },
    { key: "error", label: "error" },
  ],
  secant: [
    { key: "i", label: "i" },
    { key: "xnm1", label: "x(n-1)" },
    { key: "xn", label: "xn" },
    { key: "xnp1", label: "x(n+1)" },
    { key: "fxn", label: "f(xn)" },
    { key: "error", label: "error" },
  ],
  modified_secant: [
    { key: "i", label: "i" },
    { key: "xn", label: "xn" },
    { key: "fxn", label: "f(xn)" },
    { key: "f2", label: "f(xn + δ·xn)" },
    { key: "error", label: "error" },
  ],
};

function columnsFor(method: Method, firstStep: Step | undefined): Column[] {
  const first = SCALAR_COLUMNS[method];
  if (first) return first;

  // Dynamic columns for the matrix methods, derived from the step keys.
  const valueKeys = Object.keys(firstStep ?? {})
    .filter((k) => /^v\d+$/.test(k))
    .sort((x, y) => Number(x.slice(1)) - Number(y.slice(1)));

  // gauss_jacobi / gauss_seidel
  return [
    { key: "i", label: "i" },
    ...valueKeys.map((k, idx) => ({ key: k, label: `x${idx + 1}` })),
    { key: "error", label: "error" },
  ];
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const SYSTEM_PLACEHOLDER = "4 3 0 120\n3 4 -1 127.4\n0 -1 4 91.5";

function fmt(v: number): string {
  if (!Number.isFinite(v)) return "—";
  if (v === 0) return "0";
  return String(parseFloat(v.toPrecision(6)));
}

function fmtCell(v: number | string | undefined): string {
  if (typeof v === "string") return v;
  return typeof v === "number" ? fmt(v) : "—";
}

export default function Home() {
  const [method, setMethod] = useState<Method>("bisection");
  const [equation, setEquation] = useState("");
  const [system, setSystem] = useState("");
  const [a, setA] = useState("");
  const [b, setB] = useState("");
  const [x0, setX0] = useState("");
  const [x1, setX1] = useState("");
  const [delta, setDelta] = useState("0.01");
  const [tolerance, setTolerance] = useState("0.0001");
  const [maxIterations, setMaxIterations] = useState("50");

  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [result, setResult] = useState<SolveResult | null>(null);
  const [showSteps, setShowSteps] = useState(true);

  const isMatrix = method === "gauss_jacobi" || method === "gauss_seidel";
  const needsInterval = method === "bisection";
  const needsX0 = method === "modified_secant";
  const needsX0X1 = method === "secant";
  const needsDelta = method === "modified_secant";
  const needsTolerance = true;
  const needsMaxIterations = true;

  function clear() {
    setMethod("bisection");
    setEquation("");
    setSystem("");
    setA("");
    setB("");
    setX0("");
    setX1("");
    setDelta("0.01");
    setTolerance("0.0001");
    setMaxIterations("50");
    setFieldErrors({});
    setServerError(null);
    setResult(null);
    setShowSteps(true);
  }

  function parseSystem(): number[][] | null {
    const lines = system
      .split("\n")
      .map((l) => l.trim())
      .filter((l) => l !== "");
    if (lines.length === 0) {
      setFieldErrors({ system: "Enter the system, one row per line" });
      return null;
    }
    const rows: number[][] = [];
    for (const line of lines) {
      const numbers = line
        .split(/[\s,;]+/)
        .filter(Boolean)
        .map(Number);
      if (numbers.some((v) => !Number.isFinite(v))) {
        setFieldErrors({ system: `Row "${line}" contains an invalid number` });
        return null;
      }
      rows.push(numbers);
    }
    const n = rows.length;
    for (const row of rows) {
      if (row.length !== n + 1) {
        setFieldErrors({
          system: `The system must be square: each row needs ${n} coefficients plus 1 right-hand-side value (${n + 1} numbers per line)`,
        });
        return null;
      }
    }
    return rows;
  }

  function validate(): boolean {
    const errors: Record<string, string> = {};

    if (isMatrix) {
      if (system.trim() === "") {
        errors.system = "The system cannot be empty";
      }
    } else if (!equation.trim()) {
      errors.equation = "The equation cannot be empty";
    }

    if (needsInterval) {
      if (a.trim() === "" || !Number.isFinite(Number(a))) {
        errors.a = "Enter a valid number for a";
      }
      if (b.trim() === "" || !Number.isFinite(Number(b))) {
        errors.b = "Enter a valid number for b";
      } else if (Number(a) >= Number(b)) {
        errors.a = "a must be less than b";
      }
    }

    if (needsX0 && (x0.trim() === "" || !Number.isFinite(Number(x0)))) {
      errors.x0 = "Enter a valid number for x0";
    }

    if (needsX0X1) {
      if (x0.trim() === "" || !Number.isFinite(Number(x0))) {
        errors.x0 = "Enter a valid number for x0";
      }
      if (x1.trim() === "" || !Number.isFinite(Number(x1))) {
        errors.x1 = "Enter a valid number for x1";
      }
    }

    if (needsDelta && (delta.trim() === "" || !Number.isFinite(Number(delta)) || Number(delta) <= 0)) {
      errors.delta = "Delta must be greater than 0";
    }

    if (
      needsTolerance &&
      (tolerance.trim() === "" || !Number.isFinite(Number(tolerance)) || Number(tolerance) <= 0)
    ) {
      errors.tolerance = "Tolerance must be greater than 0";
    }

    const maxIt = Number(maxIterations);
    if (
      needsMaxIterations &&
      (maxIterations.trim() === "" || !Number.isInteger(maxIt) || maxIt <= 0)
    ) {
      errors.maxIterations = "Max iterations must be a positive integer";
    }

    setFieldErrors(errors);
    if (isMatrix && !errors.system) {
      // Parse the matrix so the exact shape error (if any) can be shown too.
      if (parseSystem() === null) return false;
    }
    return Object.keys(errors).length === 0;
  }

  async function solve() {
    setServerError(null);
    if (!validate()) return;

    setLoading(true);
    setResult(null);

    const params: Record<string, number> = {};
    if (needsInterval) {
      params.a = Number(a);
      params.b = Number(b);
    }
    if (needsX0 || needsX0X1) params.x0 = Number(x0);
    if (needsX0X1) params.x1 = Number(x1);
    if (needsDelta) params.delta = Number(delta);
    if (needsTolerance) params.tolerance = Number(tolerance);
    if (needsMaxIterations) params.max_iterations = Number(maxIterations);

    const body: Record<string, unknown> = { method, params };
    if (isMatrix) {
      body.system = parseSystem();
    } else {
      body.equation = equation;
    }

    try {
      const res = await fetch(`${API_URL}/api/solve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) {
        setServerError(data?.detail?.message ?? "Something went wrong, please try again");
        setResult(null);
      } else {
        setResult(data as SolveResult);
        setShowSteps(true);
      }
    } catch {
      setServerError("Could not reach the server, please try again");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  function renderField(
    key: "a" | "b" | "x0" | "x1" | "delta" | "tolerance" | "maxIterations",
    label: string,
    value: string,
    setValue: (v: string) => void,
    step = "any"
  ) {
    return (
      <label className={styles.field}>
        <span className={styles.fieldLabel}>{label}</span>
        <input
          type="number"
          step={step}
          dir="ltr"
          className={`${styles.input} ${fieldErrors[key] ? styles.inputError : ""}`}
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
        {fieldErrors[key] && <span className={styles.fieldError}>{fieldErrors[key]}</span>}
      </label>
    );
  }

  const columns = result ? columnsFor(result.method, result.steps[0]) : [];

  return (
    <div className={styles.page}>
      <main className={styles.main}>
        {/* Header */}
        <header className={styles.header}>
          <h1 className={styles.title}>Numerical Equation Solver</h1>
        </header>

        {/* Form */}
        <section className={styles.card}>
          <label className={styles.field}>
            <span className={styles.fieldLabel}>Method</span>
            <select
              className={styles.select}
              value={method}
              onChange={(e) => {
                setMethod(e.target.value as Method);
                setFieldErrors({});
              }}
            >
              {METHODS.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>
          </label>

          {!isMatrix && (
            <label className={`${styles.field} ${styles.fieldWide}`}>
              <span className={styles.fieldLabel}>Equation f(x) =</span>
              <input
                type="text"
                dir="ltr"
                placeholder="x^3 - x - 2"
                className={`${styles.input} ${styles.equationInput} ${fieldErrors.equation ? styles.inputError : ""}`}
                value={equation}
                onChange={(e) => setEquation(e.target.value)}
              />
              <span className={styles.helpText}>
              </span>
              {fieldErrors.equation && (
                <span className={styles.fieldError}>{fieldErrors.equation}</span>
              )}
            </label>
          )}

          {isMatrix && (
            <label className={`${styles.field} ${styles.fieldWide}`}>
              <span className={styles.fieldLabel}>System Ax = b</span>
              <textarea
                dir="ltr"
                rows={3}
                placeholder={SYSTEM_PLACEHOLDER}
                className={`${styles.input} ${styles.systemInput} ${fieldErrors.system ? styles.inputError : ""}`}
                value={system}
                onChange={(e) => setSystem(e.target.value)}
              />
              <span className={styles.helpText}>
              </span>
              {fieldErrors.system && <span className={styles.fieldError}>{fieldErrors.system}</span>}
            </label>
          )}

          <div className={styles.fieldGrid}>
            {needsInterval && (
              <>
                {renderField("a", "X_Lower", a, setA)}
                {renderField("b", "X_Upper", b, setB)}
              </>
            )}
            {(needsX0 || needsX0X1) && renderField("x0", "x0 (first guess)", x0, setX0)}
            {needsX0X1 && renderField("x1", "x1 (second guess)", x1, setX1)}
            {needsDelta && renderField("delta", "Delta (δ)", delta, setDelta)}
            {needsTolerance && renderField("tolerance", "Tolerance", tolerance, setTolerance)}
            {needsMaxIterations &&
              renderField("maxIterations", "Max iterations", maxIterations, setMaxIterations, "1")}
          </div>

          <div className={styles.actions}>
            <button className={styles.solveButton} onClick={solve} disabled={loading} type="button">
              {loading && <span className={styles.spinner} aria-hidden="true" />}
              {loading ? "Solving…" : "Solve"}
            </button>
            <button className={styles.clearButton} onClick={clear} disabled={loading} type="button">
              Clear
            </button>
          </div>
        </section>

        {/* Server / network error */}
        {serverError && (
          <div className={styles.errorBox} role="alert">
            {serverError}
          </div>
        )}

        {/* Result */}
        {result && (
          <>
            <section className={styles.card}>
              <div className={styles.resultGrid}>
                {result.root !== null && (
                  <div className={styles.metric}>
                    <span className={styles.metricLabel}>Approximate root</span>
                    <span className={styles.metricValue}>{fmt(result.root)}</span>
                  </div>
                )}
                {result.solution !== null && (
                  <div className={`${styles.metric} ${styles.metricWide}`}>
                    <span className={styles.metricLabel}>Solution</span>
                    <span className={styles.metricValue} dir="ltr">
                      {result.solution.map((v) => fmt(v)).join(" , ")}
                    </span>
                  </div>
                )}
                <div className={styles.metric}>
                  <span className={styles.metricLabel}>Number of iterations</span>
                  <span className={styles.metricValue}>{result.iterations}</span>
                </div>
                <div className={styles.metric}>
                  <span className={styles.metricLabel}>Final error</span>
                  <span className={styles.metricValue}>{fmt(result.error)}</span>
                </div>
                <div className={styles.metric}>
                  <span className={styles.metricLabel}>Method used</span>
                  <span className={styles.metricValue}>
                    {METHODS.find((m) => m.value === result.method)?.label ?? result.method}
                  </span>
                </div>
              </div>

              {result.graph && <Plot graph={result.graph} />}
            </section>

            {/* Steps table */}
            <section className={styles.card}>
              <button
                className={styles.toggleSteps}
                onClick={() => setShowSteps((s) => !s)}
                type="button"
              >
                {showSteps ? "Hide steps" : "Show steps"} ({result.steps.length})
              </button>
              {showSteps && (
                <div className={styles.tableScroll}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        {columns.map((col) => (
                          <th key={col.key}>{col.label}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.steps.map((step, i) => (
                        <tr key={i}>
                          {columns.map((col) => (
                            <td
                              key={col.key}
                              className={col.text ? styles.cellText : undefined}
                              dir={col.text ? "ltr" : undefined}
                            >
                              {fmtCell(step[col.key])}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </>
        )}
      </main>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Graph: simple SVG plot of f(x) with the root marked                        */

function Plot({ graph }: { graph: GraphData }) {
  const points = graph.points;
  if (points.length < 2) return null;

  const W = 640;
  const H = 280;
  const PAD = 12;

  const xs = points.map(([x]) => x);
  const ys = points.map(([, y]) => y);
  const xMin = Math.min(...xs);
  const xMax = Math.max(...xs);
  let yMin = Math.min(...ys);
  let yMax = Math.max(...ys);
  // Keep the axis line and root visible inside the window.
  yMin = Math.min(yMin, 0);
  yMax = Math.max(yMax, 0);
  if (yMax - yMin < 1e-12) {
    yMax = yMin + 1;
  }

  const px = (x: number) => PAD + ((x - xMin) / (xMax - xMin)) * (W - 2 * PAD);
  const py = (y: number) => H - PAD - ((y - yMin) / (yMax - yMin)) * (H - 2 * PAD);
  const clamp = (v: number) => Math.min(Math.max(v, PAD), H - PAD);

  const path = points.map(([x, y], i) => `${i === 0 ? "M" : "L"}${px(x).toFixed(2)},${clamp(py(y)).toFixed(2)}`).join(" ");

  return (
    <svg
      className={styles.plot}
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label="Plot of f(x) with the root marked"
    >
      {/* x axis */}
      <line x1={PAD} y1={py(0)} x2={W - PAD} y2={py(0)} className={styles.plotAxis} />
      {/* root marker */}
      <line
        x1={px(graph.root)}
        y1={PAD}
        x2={px(graph.root)}
        y2={H - PAD}
        className={styles.rootMarker}
      />
      <circle cx={px(graph.root)} cy={py(0)} r={4} className={styles.rootDot} />
      <path d={path} className={styles.plotLine} fill="none" />
    </svg>
  );
}
