import { motion, useScroll, useTransform } from "motion/react";
import { type FormEvent, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import desertHighway from "../assets/photos/desert-highway.jpg";
import heroForest from "../assets/photos/hero-forest.jpg";
import mountainRoad from "../assets/photos/mountain-road.jpg";
import { Reveal } from "../components/Reveal";
import { SiteNav } from "../components/SiteNav";
import { createTripPayload } from "../components/TripForm";
import { MAX_LOCATION_LENGTH, MAX_TRIP_DAYS, addIsoDays, tripLengthDays } from "../lib/tripPayload";
import { fieldClass } from "../lib/ui";
import { usePrefersReducedMotion } from "../lib/usePrefersReducedMotion";

const ease = [0.16, 1, 0.3, 1] as const;

const amberButtonClass =
  "inline-flex items-center justify-center rounded-full bg-amber px-5 py-2.5 font-marketing text-sm font-medium text-pine transition-transform duration-200 hover:-translate-y-0.5 hover:bg-amber-deep active:translate-y-0 active:scale-[0.98] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-pine";

const guideSteps = [
  {
    title: "Name the start, the end, and the days.",
    detail:
      "Enter where you leave, where you finish, and the dates. You can also set pace and a daily driving limit.",
  },
  {
    title: "Wait while the route is checked.",
    detail:
      "Planning runs as a job. You watch it draft the days, then check each drive on real roads.",
  },
  {
    title: "Read the map, then the warnings.",
    detail:
      "The map draws the driving path. Warnings flag long days, weather, or a stop that did not pass a check.",
  },
];

const checks = [
  "Driving hours from real routes",
  "Weather on the days you travel",
  "Stops that sit on the way",
];

export function LandingPage() {
  const reduce = usePrefersReducedMotion();
  const routeRef = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({
    target: routeRef,
    offset: ["start end", "end start"],
  });
  const routeShift = useTransform(scrollYProgress, [0, 1], ["-8%", "8%"]);

  useEffect(() => {
    document.title = "Roadtrip Planner";
  }, []);

  return (
    <div className="bg-sand font-marketing text-pine">
      <SiteNav />

      <section className="relative min-h-[100dvh] overflow-hidden">
        <motion.img
          src={heroForest}
          alt="Empty two-lane road through a tall evergreen forest in morning light"
          fetchPriority="high"
          className="absolute inset-0 h-full w-full object-cover"
          initial={reduce ? false : { scale: 1.06 }}
          animate={{ scale: 1 }}
          transition={{ duration: 1.6, ease }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-pine/80 via-pine/25 to-transparent" />
        <div className="relative flex min-h-[100dvh] flex-col justify-end px-4 pb-16 sm:px-8 sm:pb-20">
          <motion.div
            className="mx-auto w-full max-w-6xl"
            initial={reduce ? false : { opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.15, ease }}
          >
            <h1 className="max-w-3xl font-display text-[clamp(3.1rem,6.4vw,5.4rem)] leading-[0.95] tracking-[-0.03em] text-paper">
              The long way,
              <br />
              on purpose
            </h1>
            <p className="mt-4 max-w-md text-base text-paper/90 sm:text-lg">
              AI itineraries with driving times checked on real roads.
            </p>
            <Link to="/plan" className={`${amberButtonClass} mt-8`}>
              Plan a trip
            </Link>
          </motion.div>
        </div>
      </section>

      <section className="px-4 py-28 sm:px-8 md:py-36">
        <div className="mx-auto grid max-w-6xl gap-14 md:grid-cols-2 md:gap-16">
          <h2 className="font-display text-[clamp(2.8rem,5vw,4.25rem)] leading-[1.02] tracking-[-0.03em] md:col-start-2">
            Three stops,
            <br />
            one route
          </h2>

          <div className="md:col-start-1 md:row-span-2 md:row-start-1">
            <p className="text-sm text-pine-muted">How it works</p>
            <ol className="mt-8">
            <Reveal delay={0.08}>
                <li className="mt-2 flex items-center gap-5 border-l border-pine/20 py-4 pl-5 text-lg">
                  <span className="font-display text-xl text-pine-muted">01</span>
                  Describe the journey
                </li>
              </Reveal>
              <Reveal delay={0.08}>
                <li className="mt-2 flex items-center gap-5 border-l border-pine/20 py-4 pl-5 text-lg">
                  <span className="font-display text-xl text-pine-muted">02</span>
                  Set the days
                </li>
              </Reveal>
              <Reveal delay={0.16}>
                <li className="flex items-center gap-5 border-l border-pine/20 py-4 pl-5 text-lg">
                  <span className="font-display text-xl text-pine-muted">03</span>
                  Check the road
                </li>
              </Reveal>
            </ol>
          </div>

          <Link
            to={{ hash: "route" }}
            className="self-start font-medium text-pine underline decoration-pine/40 underline-offset-4 transition-colors duration-200 hover:decoration-pine md:col-start-2 md:self-end md:justify-self-end"
          >
            See a sample route
          </Link>
        </div>
      </section>

      <section className="px-4 pb-16 sm:px-8 md:pb-24">
        <div className="mx-auto grid max-w-6xl items-center gap-10 md:grid-cols-[1.45fr_0.85fr] md:gap-14">
          <Reveal>
            <img
              src={mountainRoad}
              alt="Mountain highway with a guardrail, pine trees, and warm light on the rock"
              className="aspect-[16/11] w-full rounded-2xl object-cover"
            />
          </Reveal>
          <Reveal delay={0.08}>
            <h2 className="font-display text-[clamp(2.6rem,4.5vw,3.75rem)] leading-[1.05] tracking-[-0.03em]">
              Checked before
              <br />
              you leave
            </h2>
            <ul className="mt-8">
              {checks.map((item) => (
                <li key={item} className="border-b border-pine/12 py-4 text-base">
                  {item}
                </li>
              ))}
            </ul>
          </Reveal>
        </div>
      </section>

      <section id="guide" className="scroll-mt-28 bg-sand-deep px-4 py-28 sm:px-8 md:py-36">
        <div className="mx-auto grid max-w-6xl items-start gap-12 lg:grid-cols-[minmax(0,0.78fr)_minmax(0,1.22fr)] lg:gap-16">
          <div>
            <p className="text-sm text-pine-muted">Before you start</p>
            <h2 className="mt-4 font-display text-[clamp(2.8rem,5vw,4.25rem)] leading-[1.02] tracking-[-0.03em]">
              A short guide
            </h2>
            <div className="mt-12 space-y-8">
              {guideSteps.map((step, index) => (
                <Reveal key={step.title} delay={index * 0.06}>
                  <p className="text-lg leading-snug">{step.title}</p>
                  <p className="mt-2 max-w-md text-sm leading-relaxed text-pine-muted">{step.detail}</p>
                </Reveal>
              ))}
            </div>
          </div>

          <Reveal delay={0.1}>
            <GuidePlanForm />
          </Reveal>
        </div>
      </section>

      <section id="route" ref={routeRef} className="relative min-h-[70vh] scroll-mt-28 overflow-hidden">
        <motion.img
          src={desertHighway}
          alt="Winding high-desert highway through pale rock in late sunlight"
          className="absolute inset-x-0 -top-[12%] h-[124%] w-full object-cover"
          style={reduce ? undefined : { y: routeShift }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-pine/70 via-transparent to-transparent" />
        <div className="relative flex min-h-[70vh] items-end justify-center px-4 pb-16">
          <p className="text-center font-display text-[clamp(2rem,4.5vw,3.25rem)] leading-tight tracking-[-0.03em] text-paper">
            Fewer Tabs, More Miles. Smarter Route Planning Powered by AI.
          </p>
        </div>
      </section>

      <section className="px-4 py-32 text-center sm:px-8 md:py-44">
        <h2 className="font-display text-[clamp(2.8rem,6vw,4.75rem)] leading-[1.02] tracking-[-0.03em]">
          Plan the next road
        </h2>
        <Link to="/plan" className={`${amberButtonClass} mt-8`}>
          Start planning
        </Link>
        <p className="mt-5 text-sm text-pine-muted">A few fields. A real route.</p>
      </section>
    </div>
  );
}

function GuidePlanForm() {
  const navigate = useNavigate();
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [error, setError] = useState<string | null>(null);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextOrigin = origin.trim();
    const nextDestination = destination.trim();
    if (!nextOrigin || !nextDestination || !startDate || !endDate) {
      setError("Enter an origin, a destination, and both dates.");
      return;
    }
    if (endDate < startDate) {
      setError("End date must be on or after the start date.");
      return;
    }
    if (tripLengthDays(startDate, endDate) > MAX_TRIP_DAYS) {
      setError(`A trip can be at most ${MAX_TRIP_DAYS} days.`);
      return;
    }

    setError(null);
    navigate("/plan", {
      state: {
        requestId: crypto.randomUUID(),
        payload: createTripPayload({
          origin: nextOrigin,
          destination: nextDestination,
          startDate,
          endDate,
        }),
      },
    });
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="w-full rounded-2xl border border-pine/15 bg-paper p-6 sm:p-8"
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block space-y-1.5 text-sm sm:col-span-1">
          <span className="font-medium">Origin</span>
          <input
            required
            maxLength={MAX_LOCATION_LENGTH}
            value={origin}
            onChange={(event) => setOrigin(event.target.value)}
            className={fieldClass}
            placeholder="San Jose, CA"
            autoComplete="off"
          />
        </label>
        <label className="block space-y-1.5 text-sm">
          <span className="font-medium">Destination</span>
          <input
            required
            maxLength={MAX_LOCATION_LENGTH}
            value={destination}
            onChange={(event) => setDestination(event.target.value)}
            className={fieldClass}
            placeholder="Monterey, CA"
            autoComplete="off"
          />
        </label>
        <label className="block space-y-1.5 text-sm">
          <span className="font-medium">Start date</span>
          <input
            required
            type="date"
            value={startDate}
            onChange={(event) => setStartDate(event.target.value)}
            className={fieldClass}
          />
        </label>
        <label className="block space-y-1.5 text-sm">
          <span className="font-medium">End date</span>
          <input
            required
            type="date"
            value={endDate}
            min={startDate || undefined}
            max={startDate ? addIsoDays(startDate, MAX_TRIP_DAYS - 1) : undefined}
            onChange={(event) => setEndDate(event.target.value)}
            className={fieldClass}
          />
        </label>
      </div>
      {error && (
        <p className="mt-4 text-sm text-clay" role="alert">
          {error}
        </p>
      )}
      <button type="submit" className={`${amberButtonClass} mt-6`}>
        Plan a trip
      </button>
    </form>
  );
}
