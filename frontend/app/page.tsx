"use client";

import { useState } from "react";
import styles from "./page.module.css";

type Method = "bisection" | "false_position" | "newton" | "secant" | "fixed_point";

const METHODS: { value: Method; label: string }[] = [
  { value: "bisection", label: "Bisection" },
  { value: "false_position", label: "False Position" },
  { value: "newton", label: "Newton-Raphson" },
  { value: "secant", label: "Secant" },
  { value: "fixed_point", label: "Fixed Point" },
];

type Step = Record<string, number>;

type GraphData = { root: number; points: number[][] };

type SolveResult = {
  method: Method;
  equation: string;
  root: number;
  iterations: number;
  error: number;
  steps: Step[];
  graph: GraphData;
};

const COLUMNS: Record<Method, { key: string; label: string }[]> = {
  bisection: [
    { key: "i", label: "i" },
    { key: "a", label: "a" },
    { key: "b", label: "b" },
    { key: "c", label: "c" },
    { key: "fc", label: "f(c)" },
    { key: "error", label: "error" },
  ],
  false_position: [
    { key: "i", label: "i" },
    { key: "a", label: "a" },
    { key: "b", label: "b" },
    { key: "c", label: "c" },
    { key: "fc", label: "f(c)" },
    { key: "error", label: "error" },
  ],
  newton: [
    { key: "i", label: "i" },
    { key: "xn", label: "xn" },
    { key: "fxn", label: "f(xn)" },
    { key: "dfxn", label: "f'(xn)" },
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
  fixed_point: [
    { key: "i", label: "i" },
    { key: "xn", label: "xn" },
    { key: "xnext", label: "x(n+1)" },
    { key: "fxn", label: "f(xn)" },
    { key: "error", label: "error" },
  ],
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function fmt(v: number): string {
  if (!Number.isFinite(v)) return "—";
  if (v === 0) return "0";
  return String(parseFloat(v.toPrecision(6)));
}

export default function Home() {
  const [method, setMethod] = useState<Method>("bisection");
  const [equation, setEquation] = useState("");
  const [a, setA] = useState("");
  const [b, setB] = useState("");
  const [x0, setX0] = useState("");
  const [x1, setX1] = useState("");
  const [tolerance, setTolerance] = useState("0.0001");
  const [maxIterations, setMaxIterations] = useState("50");

  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [result, setResult] = useState<SolveResult | null>(null);
  const [showSteps, setShowSteps] = useState(true);

  const needsInterval = method === "bisection" || method === "false_position";
  const needsX0 = method === "newton" || method === "fixed_point";
  const needsX1 = method === "secant";

  function clear() {
    setMethod("bisection");
    setEquation("");
    setA("");
    setB("");
    setX0("");
    setX1("");
    setTolerance("0.0001");
    setMaxIterations("50");
    setFieldErrors({});
    setServerError(null);
    setResult(null);
    setShowSteps(true);
  }

  function validate(): boolean {
    const errors: Record<string, string> = {};

    if (!equation.trim()) {
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

    if (needsX1 && (x1.trim() === "" || !Number.isFinite(Number(x1)))) {
      errors.x1 = "Enter a valid number for x1";
    }

    if (tolerance.trim() === "" || !Number.isFinite(Number(tolerance)) || Number(tolerance) <= 0) {
      errors.tolerance = "Tolerance must be greater than 0";
    }

    const maxIt = Number(maxIterations);
    if (
      maxIterations.trim() === "" ||
      !Number.isInteger(maxIt) ||
      maxIt <= 0
    ) {
      errors.maxIterations = "Max iterations must be a positive integer";
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }

  async function solve() {
    setServerError(null);
    if (!validate()) {
      return;
    }

    setLoading(true);
    setResult(null);

    const params: Record<string, number> = {
      tolerance: Number(tolerance),
      max_iterations: Number(maxIterations),
    };
    if (needsInterval) {
      params.a = Number(a);
      params.b = Number(b);
    }
    if (needsX0) {
      params.x0 = Number(x0);
    }
    if (needsX1) {
      params.x1 = Number(x1);
    }

    try {
      const res = await fetch(`${API_URL}/api/solve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ method, equation, params }),
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
    key: "a" | "b" | "x0" | "x1" | "tolerance" | "maxIterations",
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

  return (
    <div className={styles.page}>
      <main className={styles.main}>
        {/* Header */}
        <header className={styles.header}>
          <h1 className={styles.title}>Numerical Equation Solver</h1>
          <p className={styles.subtitle}>Choose a method, enter your equation, and get the root.</p>
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
              Use x as the variable, ^ for powers, and functions like sin(x), cos(x), exp(x), log(x).
            </span>
            {fieldErrors.equation && (
              <span className={styles.fieldError}>{fieldErrors.equation}</span>
            )}
          </label>

          <div className={styles.fieldGrid}>
            {needsInterval && (
              <>
                {renderField("a", "a (interval start)", a, setA)}
                {renderField("b", "b (interval end)", b, setB)}
              </>
            )}
            {(needsX0 || needsX1) && renderField("x0", "x0 (first guess)", x0, setX0)}
            {needsX1 && renderField("x1", "x1 (second guess)", x1, setX1)}
            {renderField("tolerance", "Tolerance", tolerance, setTolerance)}
            {renderField("maxIterations", "Max iterations", maxIterations, setMaxIterations, "1")}
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
                <div className={styles.metric}>
                  <span className={styles.metricLabel}>Approximate root</span>
                  <span className={styles.metricValue}>{fmt(result.root)}</span>
                </div>
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

              <Plot graph={result.graph} />
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
                        {COLUMNS[result.method].map((col) => (
                          <th key={col.key}>{col.label}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.steps.map((step, i) => (
                        <tr key={i}>
                          {COLUMNS[result.method].map((col) => (
                            <td key={col.key}>{fmt(step[col.key])}</td>
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
