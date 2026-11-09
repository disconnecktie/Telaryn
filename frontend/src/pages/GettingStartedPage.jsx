// Public getting-started route: connects standalone guidance to the routed sign-in boundary.

import { useNavigate } from "react-router-dom";
import GettingStartedView from "../views/GettingStartedView";

export default function GettingStartedPage() {
  const navigate = useNavigate();
  return <GettingStartedView onSignIn={() => navigate("/login")} />;
}
