// Keeps the Telaryn mark and wordmark consistent wherever product identity appears.
function AtlasMark({ className = "", decorative = false }) {
  return (
    <svg
      className={className}
      viewBox="0 0 64 64"
      role={decorative ? undefined : "img"}
      aria-hidden={decorative ? "true" : undefined}
      aria-label={decorative ? undefined : "Telaryn"}
    >
      <path
        d="M31 10H57V29L48 38V22H39V46L31 54Z"
        fill="#2488f5"
      />
      <path
        d="M7 16H43L35 25H33V48L24 57V25H16Z"
        fill="currentColor"
      />
    </svg>
  );
}

function AtlasBrand({ compact = false, className = "" }) {
  return (
    <div className={`atlas-brand ${compact ? "atlas-brand--compact" : ""} ${className}`.trim()}>
      <AtlasMark className="atlas-brand__mark" decorative />
      {!compact && <span className="atlas-brand__wordmark">TELARYN</span>}
    </div>
  );
}

export { AtlasBrand, AtlasMark };
