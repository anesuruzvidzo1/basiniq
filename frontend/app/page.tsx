import Link from "next/link";
import { ArrowRight, FileText, Database, Layers, ChevronRight } from "lucide-react";

const roles = [
  {
    title: "Reservoir Engineer",
    description:
      "Query formation statistics, well counts, and production volumes across the Alberta basin in natural language.",
    borderColor: "border-montney",
    dotColor: "bg-montney",
  },
  {
    title: "Compliance Officer",
    description:
      "Retrieve exact AER directive requirements with page-level citations. Know the source before you sign off.",
    borderColor: "border-marker",
    dotColor: "bg-marker",
  },
  {
    title: "EHS Manager",
    description:
      "Get emergency planning and environmental requirements from Directive 071 and 050 — cited to the page, instantly.",
    borderColor: "border-perf",
    dotColor: "bg-perf",
  },
];

const exampleQueries = [
  {
    category: "Regulatory",
    queries: [
      "What are the noise control requirements for well sites near residences?",
      "What waste management procedures apply to drilling operations?",
      "What are the flaring restrictions under Directive 060?",
    ],
  },
  {
    category: "Well Data",
    queries: [
      "How many active Montney wells does Tourmaline have?",
      "What is the total gas production for Cenovus in Peace River?",
      "Which licensees are currently operating in the Duvernay formation?",
    ],
  },
];

const dataStats = [
  { value: "8", label: "AER Directives indexed" },
  { value: "392+", label: "Searchable chunks" },
  { value: "200+", label: "Well records" },
  { value: "2,520", label: "Production records" },
];

const steps = [
  {
    Icon: FileText,
    step: "01",
    title: "Ask in plain language",
    body: "Type any question about Alberta regulations or well data — no query syntax, no filters.",
  },
  {
    Icon: Layers,
    step: "02",
    title: "Hybrid retrieval runs",
    body: "BasinIQ searches AER directives with BM25 and semantic search while querying the well database simultaneously.",
  },
  {
    Icon: Database,
    step: "03",
    title: "Cited answer returned",
    body: "Every regulatory claim cites the directive and page number. Every data claim shows its SQL source.",
  },
];

export default function LandingPage() {
  return (
    <main>

      {/* ── HERO: full-height split screen ── */}
      <section className="flex flex-col lg:flex-row min-h-screen">

        {/* LEFT — dark log panel */}
        <div
          className="relative lg:w-2/5 bg-log-dark flex flex-col justify-between px-10 py-16 lg:px-14 overflow-hidden"
          style={{
            backgroundImage: `
              repeating-linear-gradient(to bottom, transparent, transparent 47px, rgba(245,237,216,0.04) 47px, rgba(245,237,216,0.04) 48px),
              repeating-linear-gradient(to right, transparent, transparent 59px, rgba(245,237,216,0.04) 59px, rgba(245,237,216,0.04) 60px)
            `,
          }}
        >
          {/* Wordmark */}
          <div>
            <p className="font-lora text-6xl tracking-tight text-sidebar-text leading-none select-none">
              BASIN<span className="text-marker">IQ</span>
            </p>
            <p className="mt-3 text-xs tracking-[0.2em] uppercase text-sidebar-text/40">
              Energy Intelligence Platform
            </p>
          </div>

          {/* Capability list */}
          <div>
            <div className="border-t border-sidebar-text/10 mb-8" />
            <ul className="space-y-4">
              {[
                "AER Regulatory Directives",
                "Well License & Production Data",
                "Hybrid Retrieval + Reranking",
              ].map((cap) => (
                <li key={cap} className="flex items-center gap-3 text-sidebar-text/55 text-sm">
                  <span className="w-1.5 h-1.5 rounded-full bg-perf shrink-0" />
                  {cap}
                </li>
              ))}
            </ul>
          </div>

          {/* Attribution */}
          <p className="text-sidebar-text/25 text-xs">
            Powered by Claude · pgvector · PostgreSQL
          </p>
        </div>

        {/* RIGHT — cream content panel */}
        <div className="lg:w-3/5 bg-log-cream flex flex-col justify-center px-10 py-16 lg:px-16">

          <p className="text-montney text-xs font-medium tracking-[0.18em] uppercase mb-5">
            Alberta Upstream · Natural Language Interface
          </p>

          <h1 className="font-lora text-4xl lg:text-5xl text-body leading-[1.2] mb-6">
            Ask anything about<br />
            Alberta&rsquo;s upstream<br />
            energy sector.
          </h1>

          <p className="text-muted text-base lg:text-lg max-w-lg mb-10 leading-relaxed">
            BasinIQ connects AER regulatory directives with well license and
            production data, retrievable in natural language with page-level citations.
          </p>

          {/* Role cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-10">
            {roles.map((role) => (
              <div
                key={role.title}
                className={`bg-log-surface border-l-2 ${role.borderColor} rounded-sm p-4 shadow-sm`}
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className={`w-1.5 h-1.5 rounded-full ${role.dotColor} shrink-0`} />
                  <p className="text-xs font-semibold text-body tracking-wide">
                    {role.title}
                  </p>
                </div>
                <p className="text-xs text-muted leading-relaxed">
                  {role.description}
                </p>
              </div>
            ))}
          </div>

          {/* CTA */}
          <div>
            <Link
              href="/chat"
              className="inline-flex items-center gap-2 bg-montney hover:bg-montney-light text-white text-sm font-medium px-6 py-3 rounded-sm transition-colors"
            >
              Open BasinIQ
              <ArrowRight className="w-4 h-4" />
            </Link>
            <p className="text-muted/60 text-xs mt-3">
              Demo environment &mdash; synthetic well data, public AER directives. Not for compliance decisions.
            </p>
          </div>
        </div>
      </section>

      {/* ── EXAMPLE QUERIES ── */}
      <section className="bg-log-surface border-t border-grid py-20 px-10 lg:px-20">
        <div className="max-w-5xl mx-auto">
          <p className="text-montney text-xs font-medium tracking-[0.18em] uppercase mb-3">
            What you can ask
          </p>
          <h2 className="font-lora text-3xl text-body mb-12">
            Real questions. Cited answers.
          </h2>

          <div className="grid md:grid-cols-2 gap-10">
            {exampleQueries.map((group) => (
              <div key={group.category}>
                <p className="text-xs font-semibold text-muted uppercase tracking-widest mb-4">
                  {group.category}
                </p>
                <ul className="space-y-3">
                  {group.queries.map((q) => (
                    <li key={q}>
                      <Link
                        href={`/chat?q=${encodeURIComponent(q)}`}
                        className="group flex items-start gap-3 border border-grid rounded-sm px-4 py-3 hover:border-montney/40 hover:bg-log-cream transition-colors"
                      >
                        <ChevronRight className="w-3.5 h-3.5 text-montney mt-0.5 shrink-0 opacity-50 group-hover:opacity-100 transition-opacity" />
                        <span className="text-sm text-body/75 group-hover:text-body transition-colors leading-relaxed">
                          {q}
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ── */}
      <section className="bg-log-cream border-t border-grid py-20 px-10 lg:px-20">
        <div className="max-w-5xl mx-auto">
          <p className="text-montney text-xs font-medium tracking-[0.18em] uppercase mb-3">
            Under the hood
          </p>
          <h2 className="font-lora text-3xl text-body mb-12">
            How BasinIQ retrieves answers
          </h2>

          <div className="grid md:grid-cols-3 gap-10">
            {steps.map(({ Icon, step, title, body }) => (
              <div key={step}>
                <p className="text-xs font-mono text-montney/50 font-semibold mb-4 tracking-wider">
                  {step}
                </p>
                <div className="flex items-center gap-2 mb-3">
                  <Icon className="w-4 h-4 text-montney shrink-0" />
                  <h3 className="text-sm font-semibold text-body">{title}</h3>
                </div>
                <p className="text-sm text-muted leading-relaxed">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── DATA STATS ── */}
      <section className="bg-log-dark border-t border-sidebar-text/10 py-16 px-10 lg:px-20">
        <div className="max-w-5xl mx-auto">
          <p className="text-sidebar-text/35 text-xs tracking-[0.18em] uppercase mb-10">
            What&rsquo;s indexed
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-10">
            {dataStats.map((s) => (
              <div key={s.label}>
                <p className="font-lora text-4xl text-sidebar-text mb-1">
                  {s.value}
                </p>
                <p className="text-sidebar-text/40 text-xs">{s.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="bg-log-dark border-t border-sidebar-text/10 px-10 lg:px-20 py-8">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <p className="font-lora text-lg text-sidebar-text">
              BASIN<span className="text-marker">IQ</span>
            </p>
            <p className="text-sidebar-text/30 text-xs mt-1 max-w-sm leading-relaxed">
              Demo uses synthetic well data and publicly available AER directives.
              Not intended for regulatory compliance decisions.
            </p>
          </div>
          <div className="flex items-center gap-5 text-sidebar-text/35 text-xs">
            <Link href="/chat" className="hover:text-sidebar-text/70 transition-colors">
              Chat
            </Link>
            <a
              href="https://github.com/anesuruzvidzo1"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-sidebar-text/70 transition-colors"
            >
              GitHub
            </a>
          </div>
        </div>
      </footer>

    </main>
  );
}
