// Development journal index: presents Telaryn's verified engineering history as a chronological story.

import { Link } from "react-router-dom";
import { devlogEntries } from "../devlog/entries";

function formatMilestoneDate(date) {
  return new Date(`${date}T00:00:00`).toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export default function DevlogPage() {
  const entries = [...devlogEntries].sort(
    (a, b) => new Date(a.date) - new Date(b.date)
  );

  return (
    <div className="public-page public-page--journal">
      <section className="public-page__hero">
        <p className="eyebrow">TELARYN ENGINEERING JOURNAL</p>
        <h1>From rough idea to working system.</h1>
        <p className="public-page__lede">
          A chronological account of the product decisions, engineering
          constraints, failed assumptions, and operational work behind Telaryn.
        </p>
      </section>

      <aside className="devlog-method">
        <span>HOW THIS TIMELINE WORKS</span>
        <p>
          These chapters are reconstructed from Telaryn’s commit history,
          tickets, architecture records, and release documentation. Dates mark
          the verified milestone being discussed—not an invented publication
          schedule and not every commit that shipped that day.
        </p>
      </aside>

      <ol className="devlog-timeline">
        {entries.map((entry, index) => (
          <li key={entry.slug} className="devlog-timeline__item">
            <div className="devlog-timeline__rail" aria-hidden="true">
              <span>{String(index + 1).padStart(2, "0")}</span>
            </div>

            <article className="devlog-card">
              <div className="devlog-card__meta">
                <span>{entry.chapter}</span>
                <time dateTime={entry.date}>{formatMilestoneDate(entry.date)}</time>
              </div>

              <h2>
                <Link to={`/devlog/${entry.slug}`}>{entry.title}</Link>
              </h2>

              <p>{entry.summary}</p>

              <div className="devlog-card__footer">
                <div className="devlog-card__tags" aria-label="Topics">
                  {entry.tags.map((tag) => <span key={tag}>{tag}</span>)}
                </div>
                <Link className="devlog-card__link" to={`/devlog/${entry.slug}`}>
                  Read chapter <span aria-hidden="true">→</span>
                </Link>
              </div>
            </article>
          </li>
        ))}
      </ol>
    </div>
  );
}
