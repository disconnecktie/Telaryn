// Development journal entry page: renders one verified chapter of Telaryn's engineering history.

import { Link, useParams } from "react-router-dom";
import { getDevlogEntry } from "../devlog/entries";

function DevlogContent({ block }) {
  switch (block.type) {
    case "heading":
      return <h2>{block.text}</h2>;
    case "quote":
      return <blockquote>{block.text}</blockquote>;
    case "points":
      return <ul>{block.items.map((item) => <li key={item}>{item}</li>)}</ul>;
    case "paragraph":
    default:
      return <p>{block.text}</p>;
  }
}

function formatMilestoneDate(date) {
  return new Date(`${date}T00:00:00`).toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export default function DevlogEntryPage() {
  const { slug } = useParams();
  const entry = getDevlogEntry(slug);

  if (!entry) {
    return (
      <div className="public-page public-page--not-found">
        <p className="eyebrow">ENGINEERING JOURNAL</p>
        <h1>Entry not found</h1>
        <p>That development journal entry does not exist or may have moved.</p>
        <Link className="devlog-entry__back" to="/devlog">← Back to the engineering journal</Link>
      </div>
    );
  }

  return (
    <div className="public-page devlog-entry">
      <Link to="/devlog" className="devlog-entry__back">
        ← Engineering Journal
      </Link>

      <article>
        <header className="devlog-entry__header">
          <div className="devlog-entry__meta">
            <span>{entry.chapter}</span>
            <time dateTime={entry.date}>{formatMilestoneDate(entry.date)}</time>
          </div>
          <h1>{entry.title}</h1>
          <p className="devlog-entry__summary">{entry.summary}</p>
          <div className="devlog-card__tags" aria-label="Topics">
            {entry.tags.map((tag) => <span key={tag}>{tag}</span>)}
          </div>
        </header>

        <div className="devlog-entry__body">
          {entry.body.map((block, index) => (
            <DevlogContent key={`${entry.slug}-${index}`} block={block} />
          ))}
        </div>

        <footer className="devlog-entry__footer">
          <p>Continue through Telaryn’s engineering history.</p>
          <Link to="/devlog">Return to the journal <span aria-hidden="true">→</span></Link>
        </footer>
      </article>
    </div>
  );
}
