// Authenticated About entry: reuses the canonical public Telaryn story inside the workspace shell.

import PublicLandingView from "./PublicLandingView";

function AboutView() {
  return <PublicLandingView signedIn />;
}

export default AboutView;
