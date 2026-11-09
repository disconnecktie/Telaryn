// Shared public navigation: keeps Telaryn's product, creator, and journal pages in one coherent shell.

import { Link, NavLink, useInRouterContext } from "react-router-dom";
import { AtlasBrand } from "./AtlasBrand";
import "./PublicHeader.css";

const PUBLIC_LINKS = [
  { to: "/about", label: "Product", end: true },
  { to: "/devlog", label: "Journal" },
  { to: "/about-jay", label: "Developer", end: true },
  { to: "/getting-started", label: "Guide", end: true },
];

function PublicBrandLink() {
  const inRouter = useInRouterContext();
  const brand = <AtlasBrand className="public-brand" />;

  return inRouter ? (
    <Link to="/" className="public-site-brand" aria-label="Back to Telaryn">
      {brand}
    </Link>
  ) : (
    <a href="/" className="public-site-brand" aria-label="Back to Telaryn">
      {brand}
    </a>
  );
}

function PublicNavigationLink({ to, label, end }) {
  const inRouter = useInRouterContext();

  if (!inRouter) {
    return <a className="public-site-nav__link" href={to}>{label}</a>;
  }

  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        isActive ? "public-site-nav__link is-active" : "public-site-nav__link"
      }
    >
      {label}
    </NavLink>
  );
}

export default function PublicHeader({ onSignIn, className = "" }) {
  return (
    <header className={`public-nav public-site-header ${className}`.trim()}>
      <PublicBrandLink />

      <nav className="public-site-nav" aria-label="Public navigation">
        {PUBLIC_LINKS.map((item) => (
          <PublicNavigationLink key={item.to} {...item} />
        ))}
      </nav>

      <button className="public-sign-in-button" type="button" onClick={onSignIn}>
        Sign In <span aria-hidden="true">→</span>
      </button>
    </header>
  );
}
