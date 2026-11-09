// Public fallback page: keeps unknown Telaryn URLs inside the shared public shell.

import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <div className="public-page public-page--not-found">
      <p className="eyebrow">404</p>
      <h1>That page does not exist.</h1>
      <p>The address may be incorrect, or the page may have moved while Telaryn continues to evolve.</p>
      <div className="public-page__links">
        <Link to="/">Return to Telaryn</Link>
        <Link to="/devlog">Read the development journal</Link>
      </div>
    </div>
  );
}
