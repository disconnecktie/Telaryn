// Public terms route: exposes Telaryn's authoritative terms at a stable URL.

import { useNavigate } from "react-router-dom";
import PublicPolicyView from "../views/PublicPolicyView";

export default function TermsPage() {
  const navigate = useNavigate();
  return <PublicPolicyView policy="terms" onSignIn={() => navigate("/login")} />;
}
