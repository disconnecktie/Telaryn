// Present Telaryn's authoritative version and optional immutable build reference.
import { TELARYN_RELEASE } from "../release";
import "./ReleaseBadge.css";

export default function ReleaseBadge({ showBuild = false, className = "" }) {
  return (
    <span className={`release-badge ${className}`.trim()} aria-label={`Telaryn ${TELARYN_RELEASE.displayVersion}`}>
      <strong>Telaryn™</strong>
      <span>{TELARYN_RELEASE.displayVersion}</span>
      {showBuild && <span className="release-badge__build">Build {TELARYN_RELEASE.shortBuild}</span>}
    </span>
  );
}

