// Expose one build-time release identity to every Telaryn presentation surface.
const version = import.meta.env.VITE_TELARYN_VERSION || "0.0.0-development";
const build = import.meta.env.VITE_TELARYN_BUILD || "development";

export const TELARYN_RELEASE = Object.freeze({
  version,
  displayVersion: `v${version}`,
  build,
  shortBuild: build === "development" ? build : build.slice(0, 7),
  isReleaseCandidate: version.includes("-rc."),
});

