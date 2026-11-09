// Public privacy route: exposes Telaryn's authoritative privacy policy at a stable URL.

import { useNavigate } from "react-router-dom";
import PublicPolicyView from "../views/PublicPolicyView";

export default function PrivacyPage() {
  const navigate = useNavigate();
  return <PublicPolicyView policy="privacy" onSignIn={() => navigate("/login")} />;
}
