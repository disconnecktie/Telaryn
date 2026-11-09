// Presents deterministic workspace search and delegates navigation to the app shell.
import { useEffect, useMemo, useRef, useState } from "react";
import { searchWork } from "../api";
import "./SearchView.css";

const GROUPS = [
  ["projects", "Projects"],
  ["tickets", "Tickets"],
  ["acceptance_criteria", "Acceptance Criteria"],
  ["subtasks", "Subtasks"],
];

const EMPTY_RESULTS = {
  projects: [],
  tickets: [],
  acceptance_criteria: [],
  subtasks: [],
  total: 0,
  truncated: false,
};

function ResultCard({ result, onOpenResult }) {
  const parent = result.resource_type === "project"
    ? null
    : [result.project_reference, result.project_name, result.ticket_reference]
        .filter(Boolean)
        .join(" · ");

  return (
    <button
      type="button"
      className="search-result-card"
      onClick={() => onOpenResult(result)}
    >
      <span className="search-result-heading">
        <strong>{result.reference}</strong>
        {result.status && <span className="search-result-status">{result.status.replaceAll("_", " ")}</span>}
        {result.archived && <span className="search-result-flag">Archived</span>}
        {result.private && <span className="search-result-flag">Private</span>}
        {result.deferred && <span className="search-result-flag">Deferred</span>}
      </span>
      <span className="search-result-title">{result.title}</span>
      {parent && <span className="search-result-parent">{parent}</span>}
      <span className="search-result-match">
        <span>{result.matched_field}</span>
        {result.excerpt}
      </span>
    </button>
  );
}

function SearchView({ onOpenResult }) {
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState({
    include_completed: false,
    include_cancelled: false,
    include_deferred: false,
    include_archived: false,
  });
  const [results, setResults] = useState(EMPTY_RESULTS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const requestSequence = useRef(0);
  const normalizedQuery = query.trim();
  const canSearch = normalizedQuery.length >= 2;

  useEffect(() => {
    if (!canSearch) {
      requestSequence.current += 1;
      return undefined;
    }

    const sequence = ++requestSequence.current;
    const timer = window.setTimeout(() => {
      setLoading(true);
      setError(null);
      searchWork(normalizedQuery, filters)
        .then((payload) => {
          if (requestSequence.current === sequence) setResults(payload);
        })
        .catch((searchError) => {
          if (requestSequence.current === sequence) {
            setResults(EMPTY_RESULTS);
            setError(searchError.message);
          }
        })
        .finally(() => {
          if (requestSequence.current === sequence) setLoading(false);
        });
    }, 300);

    return () => window.clearTimeout(timer);
  }, [normalizedQuery, canSearch, filters]);

  const visibleGroups = useMemo(
    () => GROUPS.filter(([key]) => results[key]?.length),
    [results],
  );

  function changeQuery(value) {
    setQuery(value);
    if (value.trim().length < 2) {
      requestSequence.current += 1;
      setResults(EMPTY_RESULTS);
      setLoading(false);
      setError(null);
    }
  }

  function toggleFilter(name) {
    setFilters((current) => ({ ...current, [name]: !current[name] }));
  }

  return (
    <main className="main-content search-page">
      <header className="search-hero">
        <p className="eyebrow">SEARCH</p>
        <h1>Find the work you mean.</h1>
        <p>Search your authorized Projects, Tickets, Acceptance Criteria, and Subtasks. Telaryn AI is not used.</p>
      </header>

      <section className="search-panel" aria-label="Workspace search">
        <label className="search-input-label" htmlFor="workspace-search">Search Telaryn</label>
        <input
          id="workspace-search"
          className="search-input"
          type="search"
          autoComplete="off"
          value={query}
          onChange={(event) => changeQuery(event.target.value)}
          placeholder="Title, description, purpose, or reference"
          autoFocus
        />
        <div className="search-filter-row" aria-label="Include additional work">
          {[
            ["include_completed", "Completed"],
            ["include_cancelled", "Cancelled"],
            ["include_deferred", "Deferred"],
            ["include_archived", "Archived Projects"],
          ].map(([name, label]) => (
            <label key={name}>
              <input
                type="checkbox"
                checked={filters[name]}
                onChange={() => toggleFilter(name)}
              />
              <span>{label}</span>
            </label>
          ))}
        </div>
      </section>

      <section className="search-results" aria-live="polite" aria-busy={loading}>
        {!normalizedQuery && (
          <div className="search-guidance">
            <strong>Search across your workspace.</strong>
            <p>Try a phrase you remember, or a reference such as TKT-049 or PRJ-001.</p>
          </div>
        )}
        {normalizedQuery && !canSearch && (
          <p className="search-guidance">Enter at least two characters to search.</p>
        )}
        {loading && <p className="search-guidance">Searching authorized work…</p>}
        {error && (
          <div className="search-guidance search-error" role="alert">
            <strong>Telaryn could not complete the search.</strong>
            <p>{error}</p>
          </div>
        )}
        {!loading && !error && canSearch && results.total === 0 && (
          <div className="search-guidance">
            <strong>No matching work found.</strong>
            <p>Try another phrase or include completed, deferred, or archived work.</p>
          </div>
        )}
        {!loading && !error && visibleGroups.map(([key, label]) => (
          <section className="search-result-group" key={key}>
            <div className="search-result-group-heading">
              <h2>{label}</h2>
              <span>{results[key].length}</span>
            </div>
            <div className="search-result-list">
              {results[key].map((result) => (
                <ResultCard key={`${result.resource_type}-${result.id}`} result={result} onOpenResult={onOpenResult} />
              ))}
            </div>
          </section>
        ))}
        {!loading && results.truncated && (
          <p className="search-limit-note">Showing the closest matches. Refine your search to narrow the results.</p>
        )}
      </section>
    </main>
  );
}

export default SearchView;

