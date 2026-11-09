// Development journal content: a repository-grounded chronology of Telaryn's product and engineering milestones.

export const devlogEntries = [
  {
    slug: "why-i-built-telaryn",
    title: "Why I Built Telaryn",
    date: "2026-08-16",
    chapter: "Origin · The first working system",
    summary: "Telaryn began with a recurring operational problem: important work almost never arrives already organized.",
    tags: ["Product origin", "Work design", "AI"],
    body: [
      { type: "paragraph", text: "Important work rarely begins as a perfectly written task. It begins as a conversation, an email, a meeting, a vague requirement, or somebody saying that something needs to be figured out." },
      { type: "paragraph", text: "Across operational leadership, intelligence work, and technical projects, the same translation burden kept appearing: people had to turn incomplete context into something concrete enough to execute, review, and explain later." },
      { type: "heading", text: "The first boundary mattered more than the first feature" },
      { type: "paragraph", text: "The repository began on August 16 with a small ticket API. Projects, subtasks, an AI review data model, a provider abstraction, an approval workflow, and the first React interface followed the same day. The speed was useful, but the governing rule was more important than the feature count." },
      { type: "quote", text: "AI proposes. Humans approve. Telaryn records." },
      { type: "paragraph", text: "AI output would remain advisory. A person would decide what became authoritative work. That constraint shaped the application from its first working version and later became part of Telaryn’s public identity." }
    ]
  },
  {
    slug: "making-work-traceable",
    title: "Making Work Traceable, Not Merely Editable",
    date: "2026-08-24",
    chapter: "Execution · Authority and history",
    summary: "A task tracker can change fields. A trustworthy work system must explain what changed, why it changed, and who approved it.",
    tags: ["Activity", "Atomic changes", "Human control"],
    body: [
      { type: "paragraph", text: "The early interface could create and edit work, but ordinary editing was not enough. Status changes, progress, acceptance criteria, and subtasks were all parts of one decision surface. Saving them as unrelated mutations would create a technically correct database and a misleading history." },
      { type: "heading", text: "One reviewed decision, one durable record" },
      { type: "paragraph", text: "By August 24, ticket editing had moved toward atomic drawer-session commits, unified Activity, auditable deferred scope, bulk structure entry, and explicit recovery for stalled AI reviews." },
      { type: "points", items: ["Human-authored changes remain distinguishable from AI proposals.", "Related edits commit together instead of leaving partial state.", "Deferred work keeps its reason and can be restored.", "Activity tells the story of the decision rather than listing database noise."] },
      { type: "paragraph", text: "That work established a pattern repeated throughout Telaryn: the interface may simplify a workflow, but it must not erase authority, provenance, or recovery behavior to do it." }
    ]
  },
  {
    slug: "designing-my-work",
    title: "Designing My Work Around Attention",
    date: "2026-08-27",
    chapter: "Focus · Personal execution",
    summary: "The product stopped treating every open ticket as equally important and began helping one person decide what deserves attention now.",
    tags: ["My Work", "Current Focus", "UX"],
    body: [
      { type: "paragraph", text: "A project browser answers what exists. It does not answer what should receive attention next. Telaryn needed a personal execution surface that could reduce noise without pretending to make the decision for the user." },
      { type: "heading", text: "One focus, visible alternatives" },
      { type: "paragraph", text: "My Work introduced a user-chosen Current Focus, deterministic alternatives, recommended next subtasks, attention signals, and intentionally unavailable work. Choosing focus did not silently change ticket status, assignment, or priority." },
      { type: "paragraph", text: "This was a subtle product decision. Recommendation and authority had to remain separate even in a feature designed to be helpful. Telaryn could make the next useful action easier to see; the person still decided what mattered." }
    ]
  },
  {
    slug: "human-governed-project-review",
    title: "Building Human-Governed Project Review",
    date: "2026-08-28",
    chapter: "Intelligence · Bounded review",
    summary: "Project Review became the clearest test of whether Telaryn could use AI deeply without surrendering control.",
    tags: ["Project Review", "Evidence", "Governance"],
    body: [
      { type: "paragraph", text: "Reviewing a whole project is more consequential than improving a ticket description. It requires a stable evidence set, privacy boundaries, durable execution, explainable findings, and a safe path from proposal to action." },
      { type: "heading", text: "The review became a workflow, not a prompt" },
      { type: "points", items: ["A versioned authorized snapshot defines exactly what the provider may inspect.", "Generation runs as a durable background job rather than depending on the browser staying open.", "Evidence references must resolve to the submitted snapshot.", "Each proposal can be approved, rejected, or deferred before anything changes.", "Approved changes receive an exact final preview and apply atomically after freshness checks."] },
      { type: "paragraph", text: "The first snapshot foundation landed August 28. Presentation, persistent decisions, constrained candidate edits, and atomic application followed across August 28–29. The result was not autonomous project management. It was a bounded review system in which the model could reason broadly and the human retained final authority." }
    ]
  },
  {
    slug: "from-local-to-operable",
    title: "Crossing the Local-Application Boundary",
    date: "2026-09-02",
    chapter: "Platform · From laptop to service",
    summary: "Containerization and PostgreSQL forced Telaryn to become reproducible before it could become publicly reachable.",
    tags: ["Containers", "PostgreSQL", "Operations"],
    body: [
      { type: "paragraph", text: "A local SQLite application can hide assumptions about persistence, startup order, networking, migration ownership, and recovery. Moving beyond the laptop meant making those assumptions explicit." },
      { type: "paragraph", text: "On September 2, Telaryn gained a containerized integration environment, PostgreSQL compatibility, and migration proof. The gateway, backend, database, and one-shot migration path could now be exercised together without touching the native development database." },
      { type: "heading", text: "Deployment became part of the product" },
      { type: "paragraph", text: "This was the start of a longer operational story: same-origin API routing, internal-only backend ingress, managed secrets, bounded diagnostics, immutable builds, backup verification, clean-server recovery, and compatible rollback. Reachability alone would never count as readiness." }
    ]
  },
  {
    slug: "building-capture-work",
    title: "Teaching Capture Work to Respect Ambiguity",
    date: "2026-09-16",
    chapter: "Intake · From context to action",
    summary: "Capture Work turned Telaryn’s original idea into a deliberate workflow: begin with incomplete input, compare it with authorized work, and propose a useful next shape.",
    tags: ["Capture Work", "AI", "Product design"],
    body: [
      { type: "paragraph", text: "Users should not need to know whether an input is a Project, a Ticket, an update, or supporting context before they record it. That classification is part of the work Telaryn is supposed to reduce." },
      { type: "paragraph", text: "The guided intake flow landed September 16 with bounded workspace comparison, structured proposals, and human review before creation. Later refinements made clarification adaptive rather than mandatory and distinguished supported, inferred, and recommended material." },
      { type: "heading", text: "Proposal is not authority" },
      { type: "paragraph", text: "The generated structure never becomes authoritative merely because it sounds plausible. The user proceeds through a normal Project or Ticket draft, reviews the proposed definition of done and next actions, and chooses what to create." },
      { type: "quote", text: "The useful outcome is not a confident answer. It is a better decision surface." }
    ]
  },
  {
    slug: "from-atlas-to-telaryn",
    title: "From Atlas Waypoint to Telaryn",
    date: "2026-09-20",
    chapter: "Identity · Naming the product",
    summary: "The project outgrew its working name just as it began to outgrow the boundaries of a personal task tracker.",
    tags: ["Brand", "Product", "Release identity"],
    body: [
      { type: "paragraph", text: "The project began as Atlas and briefly carried the fuller Atlas Waypoint identity. The name worked while the application was primarily an internal development project." },
      { type: "paragraph", text: "By September, the product included governed AI review, personal focus, privacy controls, workspace isolation, search, reports, feedback, mobile execution, and a serious deployment architecture. It needed an identity that belonged to the product rather than the prototype." },
      { type: "heading", text: "A rename as an engineering forcing function" },
      { type: "paragraph", text: "The Telaryn rebrand landed September 20. It required more than replacing visible text: release identity, domain ownership, public language, icons, deployment configuration, documentation, and legacy assumptions all had to be reconciled." },
      { type: "paragraph", text: "The new line—Every action has a purpose—captured the product more accurately. Telaryn was not simply organizing tasks. It was preserving the relationship between context, decisions, action, and outcome." }
    ]
  },
  {
    slug: "moving-telaryn-to-azure",
    title: "Proving Telaryn in Azure",
    date: "2026-09-21",
    chapter: "Staging · Security and recovery",
    summary: "The first real deployment exposed every place where local confidence had to become operational evidence.",
    tags: ["Azure", "Security", "Recovery"],
    body: [
      { type: "paragraph", text: "The Azure staging foundation introduced Container Apps, PostgreSQL, Key Vault, managed identity, private networking, HTTPS, Entra protection, bounded logging, and scripted deployment gates." },
      { type: "paragraph", text: "The first deployment was not a clean victory lap. Gateway routing, identity-provider arguments, secret handling, migration identity, PowerShell serialization, and recovery tooling all produced concrete failures that had to be understood and corrected." },
      { type: "heading", text: "Evidence over optimism" },
      { type: "paragraph", text: "By September 24–25, the staging path could prove public gateway reachability, internal backend isolation, migration success, backup and clean-server recovery, rollback compatibility, log retention, and ingestion limits. The runbooks record what must be true, not merely what usually works." },
      { type: "paragraph", text: "That operational discipline became one of Telaryn’s defining engineering lessons: a system is not ready because it deployed once. It is ready when its boundaries and recovery path can be demonstrated repeatedly." }
    ]
  },
  {
    slug: "shipping-the-first-release-candidate",
    title: "What RC1 Actually Meant",
    date: "2026-09-25",
    chapter: "Release · Defining ready",
    summary: "RC1 was not a claim that Telaryn was finished. It was a commitment to a coherent identity, verified boundaries, and an operable baseline.",
    tags: ["RC1", "Production", "Quality"],
    body: [
      { type: "paragraph", text: "Telaryn v1.0.0-rc.1 received its canonical release identity on September 25. The version and immutable build commit became visible in the product, and the public baseline gained clear About, Privacy, Terms, ownership, and support information." },
      { type: "heading", text: "Ready had to mean more than feature complete" },
      { type: "points", items: ["Frontend, backend, infrastructure, and container checks run as automated quality gates.", "Public pages and protected application boundaries are tested independently.", "Production uses its own persistence, secrets, logging, identity, email, DNS, backup, recovery, and rollback evidence.", "AI remains optional and bounded; core work management remains usable without it.", "Release identity ties the running interface to one reviewed source commit."] },
      { type: "paragraph", text: "The production foundation followed on September 26, along with invitation delivery and first-run guidance. RC1 marked the point where Telaryn could be discussed as a real, operated product while still being honest about its early-release status." },
      { type: "quote", text: "A release candidate is not the end of development. It is the point where readiness becomes a claim that must be supported with evidence." }
    ]
  }
];

export function getDevlogEntry(slug) {
  return devlogEntries.find((entry) => entry.slug === slug);
}
