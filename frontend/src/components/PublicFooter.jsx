// Provide consistent public release, ownership, policy, and contact information.
import { Link, useInRouterContext } from "react-router-dom";
import { AtlasBrand } from "./AtlasBrand";
import ReleaseBadge from "./ReleaseBadge";
import "./PublicFooter.css";

function resetPublicScroll() {
  document.documentElement.scrollTop = 0;
  document.body.scrollTop = 0;
}

function PublicInternalLink({ to, children }) {
  const inRouter = useInRouterContext();

  if (inRouter) {
    return <Link to={to} onClick={resetPublicScroll}>{children}</Link>;
  }

  return <a href={to} onClick={resetPublicScroll}>{children}</a>;
}

export default function PublicFooter() {
  return (
    <footer className="public-footer">
      <div className="public-footer__brand">
        <AtlasBrand className="public-footer__wordmark" />
        <p>Human-governed work intelligence for turning context into purposeful action.</p>
        <ReleaseBadge showBuild />
      </div>
      <div className="public-footer__links">
        <nav aria-label="Public information">
          <strong>Explore</strong>
          <PublicInternalLink to="/about">About Telaryn</PublicInternalLink>
          <PublicInternalLink to="/about-jay">About Jay</PublicInternalLink>
          <PublicInternalLink to="/devlog">Engineering Journal</PublicInternalLink>
          <PublicInternalLink to="/getting-started">Getting Started</PublicInternalLink>
          <PublicInternalLink to="/privacy">Privacy</PublicInternalLink>
          <PublicInternalLink to="/terms">Terms</PublicInternalLink>
        </nav>
        <nav aria-label="Contact Telaryn">
          <strong>Contact</strong>
          <a href="mailto:support@telaryn.app">Support</a>
          <a href="mailto:privacy@telaryn.app">Privacy requests</a>
          <a href="mailto:security@telaryn.app">Security reports</a>
        </nav>
      </div>
      <p className="public-footer__copyright">© 2026 Jay Hughes. All rights reserved.</p>
    </footer>
  );
}
