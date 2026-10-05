import { motion } from "motion/react";
import { useEffect } from "react";
import canyonDusk from "../assets/photos/canyon-dusk.jpg";
import { SiteNav } from "../components/SiteNav";
import { projects } from "../content/projects";
import { usePrefersReducedMotion } from "../lib/usePrefersReducedMotion";

const ease = [0.16, 1, 0.3, 1] as const;

const linkClass =
  "font-medium text-pine underline decoration-pine/40 underline-offset-4 transition-colors duration-200 hover:decoration-pine focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-pine";

export function ProjectsPage() {
  const reduce = usePrefersReducedMotion();

  useEffect(() => {
    document.title = "Other work | Roadtrip Planner";
  }, []);

  return (
    <div className="min-h-[100dvh] bg-sand font-marketing text-pine">
      <SiteNav />
      <section className="relative min-h-[68vh] overflow-hidden">
        <motion.img
          src={canyonDusk}
          alt="River canyon at dusk, with amber light on the cliff and a road along the water"
          className="absolute inset-0 h-full w-full object-cover"
          initial={reduce ? false : { scale: 1.06 }}
          animate={{ scale: 1 }}
          transition={{ duration: 1.5, ease }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-pine/80 via-pine/20 to-pine/10" />
        <div className="relative flex min-h-[68vh] flex-col justify-end px-4 pb-14 sm:px-8 sm:pb-16">
          <div className="mx-auto w-full max-w-6xl">
            <h1 className="max-w-xl font-display text-[clamp(3.25rem,7vw,5.5rem)] leading-[0.95] tracking-[-0.03em] text-paper">
              Other work
            </h1>
            <p className="mt-3 max-w-md text-lg text-paper/90">Projects beyond the road.</p>
          </div>
        </div>
      </section>

      <section className="px-4 py-24 sm:px-8 md:py-32">
        <div className="mx-auto max-w-6xl">
          {projects.length === 0 ? (
            <p className="max-w-md text-lg leading-relaxed">No other projects are listed yet.</p>
          ) : (
            <ul className="grid gap-16">
              {projects.map((project, index) => (
                <motion.li
                  key={project.href}
                  className="grid gap-3 border-t border-pine/10 pt-8 md:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)] md:items-end md:gap-16"
                  initial={reduce ? false : { opacity: 0, y: 28 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, amount: 0.35 }}
                  transition={{ duration: 0.7, delay: Math.min(index, 4) * 0.04, ease }}
                >
                  <h2 className="font-display text-[clamp(2rem,4vw,3.25rem)] leading-none tracking-[-0.03em]">
                    {project.name}
                  </h2>
                  <div>
                    {project.description && (
                      <p className="max-w-md text-base leading-relaxed">{project.description}</p>
                    )}
                    {project.language && (
                      <p className={`text-sm text-pine-muted ${project.description ? "mt-2" : ""}`}>
                        {project.language}
                      </p>
                    )}
                    <a
                      href={project.href}
                      className={`${linkClass} mt-4 inline-flex`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      View on GitHub
                    </a>
                  </div>
                </motion.li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </div>
  );
}
