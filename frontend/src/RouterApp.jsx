// Browser router: adds stable public URLs around the existing Telaryn product coordinator.

import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import App from "./App";
import PublicPageLayout from "./components/public/PublicPageLayout";
import AboutPage from "./pages/AboutPage";
import AboutJay from "./pages/AboutJay";
import DevlogEntryPage from "./pages/DevlogEntryPage";
import DevlogPage from "./pages/DevlogPage";
import GettingStartedPage from "./pages/GettingStartedPage";
import LoginPage from "./pages/LoginPage";
import NotFoundPage from "./pages/NotFoundPage";
import PrivacyPage from "./pages/PrivacyPage";
import TermsPage from "./pages/TermsPage";

const LEGACY_PUBLIC_HASHES = {
  "#/": "/about",
  "#/getting-started": "/getting-started",
  "#/privacy": "/privacy",
  "#/terms": "/terms",
};

function ProductRoute() {
  const { hash } = useLocation();
  const legacyDestination = LEGACY_PUBLIC_HASHES[hash];

  if (legacyDestination) {
    return <Navigate to={legacyDestination} replace />;
  }

  return <App />;
}

export default function RouterApp() {
  return (
    <Routes>
      <Route path="/" element={<ProductRoute />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/about" element={<AboutPage />} />
      <Route path="/getting-started" element={<GettingStartedPage />} />
      <Route path="/privacy" element={<PrivacyPage />} />
      <Route path="/terms" element={<TermsPage />} />

      <Route element={<PublicPageLayout />}>
        <Route path="/about-jay" element={<AboutJay />} />
        <Route path="/devlog" element={<DevlogPage />} />
        <Route path="/devlog/:slug" element={<DevlogEntryPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
