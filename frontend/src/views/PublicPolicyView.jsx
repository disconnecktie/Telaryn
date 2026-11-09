// Publish concise RC1 Privacy and Terms information outside the authenticated boundary.
import PublicHeader from "../components/PublicHeader";
import PublicFooter from "../components/PublicFooter";
import "./PublicPolicyView.css";

const POLICY_CONTENT = {
  privacy: {
    eyebrow: "TELARYN PRIVACY",
    title: "Privacy should be understandable.",
    intro: "This notice explains what Telaryn handles, why it is needed, and the choices available to you during the RC1 release.",
    sections: [
      ["Who operates Telaryn", <p key="operator">Telaryn is operated by Jay Hughes as a United States-based independent software project. Privacy questions and applicable data-rights requests may be sent to <a href="mailto:privacy@telaryn.app">privacy@telaryn.app</a>.</p>],
      ["Information Telaryn handles", <ul key="information"><li>Account identity, workspace membership, authentication records, and preferences.</li><li>Projects, tickets, acceptance criteria, subtasks, updates, reports, and other content you choose to create.</li><li>Access requests and invitation history, including the contact information and context submitted with a request.</li><li>Feedback text, bounded browser and route context, reviewer history, and any screenshot you deliberately attach. Uploaded screenshots are re-encoded to remove embedded image metadata, but visible information in the image is not automatically redacted.</li><li>Operational and security diagnostics. Telaryn’s application-generated diagnostic events use restricted fields and are designed not to include work content, credentials, cookies, request bodies, or raw AI responses. Hosting-provider logging and backup behavior also depend on deployment configuration.</li></ul>],
      ["How information is used", <p key="use">Telaryn uses this information to provide and secure the service, isolate workspaces, preserve requested work history, process access requests, deliver support, investigate feedback, recover from failures, and improve the product. Telaryn does not sell personal information or use it for third-party advertising.</p>],
      ["AI-assisted features", <p key="ai">AI processing occurs only when an eligible user deliberately invokes an AI-assisted workflow. Telaryn sends the bounded context selected for that operation to the configured provider and presents the result as a proposal requiring human approval. Private Projects and Tickets are excluded from AI workflows under Telaryn’s current controls. Provider processing is also subject to the provider configuration and terms applicable to the deployed service.</p>],
      ["Hosting and service providers", <p key="hosting">The RC1 service uses Microsoft Azure for hosting, PostgreSQL persistence, encrypted secrets, identity protection, email delivery, diagnostics, backup, and recovery. Microsoft Entra may protect access to pre-public or restricted environments. An AI provider receives bounded content only for user-initiated AI operations.</p>],
      ["Retention", <ul key="retention"><li>Workspace and account data remain until they are deleted through an available product or administrative process, or until the service is discontinued.</li><li>Access requests expire after 90 days and are no longer available for review after expiry. Expired request records and their linked invitation history are deleted when a new access request triggers cleanup or an administrator runs the retention command. Protected backups expire separately.</li><li>The documented Azure production infrastructure configures operational log retention for 30 days. Actual retention depends on the deployed configuration; backups or separately retained security records may have different lifetimes.</li><li>Closed feedback follows a defined retention policy: screenshots are eligible for removal 90 days after closure, and closed feedback records and reviewer history are eligible for deletion 365 days after closure. The administrative retention command performs this cleanup when run; the application does not independently schedule it. Feedback that remains open is not covered by these closed-feedback deletion rules. Protected backups expire separately.</li></ul>],
      ["Security and your choices", <p key="choices">Use Telaryn only for information you are authorized to store and do not submit classified information, credentials, authentication tokens, or unnecessarily sensitive personal information. Contact <a href="mailto:security@telaryn.app">security@telaryn.app</a> for suspected vulnerabilities, <a href="mailto:support@telaryn.app">support@telaryn.app</a> for assistance, or the privacy address above to ask about your information.</p>],
      ["Changes", <p key="changes">This notice is effective September 25, 2026. Material changes will be reflected on this page with an updated effective date.</p>],
    ],
  },
  terms: {
    eyebrow: "TELARYN TERMS",
    title: "Clear expectations for an early release.",
    intro: "These terms govern access to the Telaryn RC1 service. By using Telaryn, you agree to use it responsibly and within the authority granted to your account.",
    sections: [
      ["Release-candidate service", <p key="rc">Telaryn v1.0.0-rc.1 is prerelease software provided for evaluation and early use. Features, availability, storage practices, and interfaces may change before v1.0.0. Access may be limited, paused, or discontinued while the service is improved or protected.</p>],
      ["Accounts and access", <p key="accounts">Access is personal, invitation-based, and limited to the workspaces and administrative capabilities explicitly assigned to your account. Keep credentials secure, do not share sessions or invitations, and promptly report suspected unauthorized access. Approval of an access request does not guarantee an account or continued service.</p>],
      ["Permission to use the service", <p key="service-permission">An approved account gives you permission to access and use the hosted Telaryn application within the capabilities and workspaces assigned to you, subject to these terms. It does not grant a license to the underlying source code, permission to host another instance, or permission to resell the software.</p>],
      ["Acceptable use", <ul key="acceptable"><li>Use Telaryn only for lawful purposes and information you are authorized to manage.</li><li>Do not upload classified information, malware, credentials, authentication material, or content that violates another person’s rights.</li><li>Do not probe, bypass, overload, scrape, reverse engineer, or interfere with Telaryn’s security or access controls except through an expressly authorized security test.</li><li>Do not misrepresent AI proposals as authoritative decisions without the required human review.</li></ul>],
      ["Your content", <p key="content">You retain ownership of the content you submit. You grant Telaryn the limited permission needed to host, process, transmit, back up, and display that content to operate the service and perform workflows you deliberately request. You remain responsible for the content and for obtaining any permissions required to use it.</p>],
      ["Telaryn ownership and publicly visible code", <p key="ownership">The original, protectable Telaryn software, interface, design, and documentation are proprietary works owned by Jay Hughes, subject to third-party licenses and applicable law. Telaryn™ identifies the product. If source code is published on GitHub, people may view and fork it through the permissions provided by GitHub; publication is not an open-source license and does not otherwise authorize modification, redistribution, self-hosting, resale, or commercial reuse of Telaryn code without separate permission. This ownership notice does not claim exclusive copyright over general ideas or functionality.</p>],
      ["AI-assisted output", <p key="output">AI-generated or AI-assisted output may be incomplete or wrong. It is advisory and must be reviewed before use. You are responsible for decisions made from a proposal and for verifying information before relying on it.</p>],
      ["No warranty", <p key="warranty">To the maximum extent permitted by applicable law, Telaryn RC1 is provided “as is” and “as available,” without warranties of uninterrupted availability, fitness for a particular purpose, accuracy, or freedom from defects. Nothing in these terms excludes rights or liability that cannot legally be excluded.</p>],
      ["Suspension and changes", <p key="suspension">Access may be suspended or terminated to protect users or the service, address misuse, comply with law, or end the RC1 program. These terms may change as Telaryn approaches general release. Continued use after a posted change indicates acceptance of the revised terms.</p>],
      ["Contact", <p key="contact">These terms are effective September 25, 2026. Contact <a href="mailto:support@telaryn.app">support@telaryn.app</a> with service questions or <a href="mailto:security@telaryn.app">security@telaryn.app</a> to report a security concern.</p>],
    ],
  },
};

export default function PublicPolicyView({ policy, onSignIn }) {
  const content = POLICY_CONTENT[policy] || POLICY_CONTENT.privacy;
  return (
    <main className="public-policy-page">
      <PublicHeader onSignIn={onSignIn} className="public-policy-nav" />
      <article className="public-policy">
        <header className="public-policy__hero">
          <p className="eyebrow">{content.eyebrow}</p>
          <h1>{content.title}</h1>
          <p>{content.intro}</p>
        </header>
        <div className="public-policy__sections">
          {content.sections.map(([heading, body]) => (
            <section key={heading}>
              <h2>{heading}</h2>
              {body}
            </section>
          ))}
        </div>
      </article>
      <PublicFooter />
    </main>
  );
}

