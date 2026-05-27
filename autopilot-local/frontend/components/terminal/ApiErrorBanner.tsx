"use client";

export function ApiErrorBanner({
  message,
  hint,
}: {
  message: string;
  hint?: string;
}) {
  return (
    <div
      role="alert"
      style={{
        marginBottom: 14,
        padding: "10px 14px",
        borderRadius: 8,
        border: "1px solid var(--red)",
        background: "rgba(239, 68, 68, 0.08)",
        fontSize: 13,
        color: "var(--text)",
      }}
    >
      <strong style={{ color: "var(--red)" }}>{message}</strong>
      {hint ? (
        <p style={{ margin: "6px 0 0", color: "var(--text-muted)", fontSize: 12 }}>{hint}</p>
      ) : null}
    </div>
  );
}
