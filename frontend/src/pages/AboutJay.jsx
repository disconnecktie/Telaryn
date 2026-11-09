// Public creator profile: connects Jay Hughes's operational background to the product choices behind Telaryn.

export default function AboutJay() {
  return (
    <div className="public-page public-profile">
      <section className="public-page__hero">
        <p className="eyebrow">THE PERSON BEHIND TELARYN</p>
        <h1>Operator. Builder. Problem solver.</h1>

        <p className="public-page__lede">
          I’m Jay Hughes. I spent more than two decades in the U.S. Air Force
          and Intelligence Community working where operations, leadership,
          technology, and consequential decisions meet.
        </p>
      </section>

      <section>
        <p className="public-section-marker">01 · THE THROUGHLINE</p>
        <h2>Make complicated work easier to understand.</h2>

        <p>
          Much of my career has involved taking difficult operational problems
          and making the information, processes, and tools around them more
          useful. I began using Python and data tools in operational
          environments years before I considered myself a software developer.
        </p>

        <p>
          The goal was rarely software for its own sake. It was to eliminate
          friction, reduce repetitive work, expose information more clearly, or
          help someone make a better decision.
        </p>
      </section>

      <section>
        <p className="public-section-marker">02 · FROM OPERATIONS TO SOFTWARE</p>
        <h2>Build the missing tool.</h2>

        <p>
          That problem-solving habit led deeper into application development,
          automation, data workflows, APIs, cloud deployment, and AI-assisted
          systems. Telaryn is the most complete expression of that progression:
          product thinking, engineering, security, operations, and design held
          together by one practical question—does this help a person move real
          work forward?
        </p>
      </section>

      <section>
        <p className="public-section-marker">03 · WHY TELARYN</p>
        <h2>Important work rarely arrives organized.</h2>

        <p>
          It begins as a conversation, an email, a briefing, a vague
          requirement, or somebody saying, “We need to figure this out.”
          Telaryn began as an attempt to capture that ambiguity and turn it
          into work a person can actually execute.
        </p>

        <p>
          The governing constraint came from experience: AI can help shape and
          examine work, but it should not quietly become the authority. Telaryn
          proposes. A human decides. The system preserves what happened.
        </p>
      </section>

      <section>
        <p className="public-section-marker">04 · NOW</p>
        <h2>Continuing the work.</h2>

        <p>
          I’m developing Telaryn while transitioning from military service into
          civilian technology and national-security work. I’m particularly
          interested in software development, AI-enabled workflows, data and
          automation, intelligence systems, and technical roles where
          operational experience is useful rather than incidental.
        </p>
      </section>

      <section className="public-profile__elsewhere">
        <div>
          <p className="public-section-marker">ELSEWHERE</p>
          <h2>Follow the work or start a conversation.</h2>
          <p>
            The engineering journal tells the product story. LinkedIn carries
            the professional one, and GitHub shows the public work.
          </p>
        </div>

        <div className="public-profile__links">
          <a className="public-profile-link" href="https://www.linkedin.com/in/jay-hughes-93621088" target="_blank" rel="noreferrer">
            <span><small>Professional</small>LinkedIn</span>
            <span aria-hidden="true">↗</span>
          </a>
          <a className="public-profile-link" href="https://github.com/disconnecktie" target="_blank" rel="noreferrer">
            <span><small>Code</small>GitHub</span>
            <span aria-hidden="true">↗</span>
          </a>
        </div>
      </section>
    </div>
  );
}
