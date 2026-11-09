// Public page layout: extends Telaryn's established presentation for creator and journal content.

import { useEffect } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import PublicFooter from "../PublicFooter";
import PublicHeader from "../PublicHeader";
import "../../views/PublicLandingView.css";
import "./PublicPageLayout.css";

export default function PublicPageLayout() {
  const { pathname } = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
  }, [pathname]);

  return (
    <main className="public-landing public-about-page public-routed-page">
      <a className="public-routed-skip-link" href="#public-content">
        Skip to content
      </a>

      <PublicHeader onSignIn={() => navigate("/login")} />

      <div id="public-content" className="public-routed-content">
        <Outlet />
      </div>

      <PublicFooter />
    </main>
  );
}
