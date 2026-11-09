// Stable public About route: preserves the production Telaryn product presentation.

import { useNavigate } from "react-router-dom";
import PublicLandingView from "../views/PublicLandingView";

export default function AboutPage() {
  const navigate = useNavigate();
  return <PublicLandingView onSignIn={() => navigate("/login")} />;
}
