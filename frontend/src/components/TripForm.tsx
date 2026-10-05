import type { FormEvent } from "react";
import { useState } from "react";
import type { TripRequestPayload } from "../api/client";
import type { Budget, Pace } from "../lib/tripPayload";
import {
  MAX_INTERESTS_LENGTH,
  MAX_LOCATION_LENGTH,
  MAX_NOTES_LENGTH,
  MAX_TRIP_DAYS,
  addIsoDays,
  parseCommaList,
  tripLengthDays,
} from "../lib/tripPayload";
import { fieldClass, primaryButtonClass } from "../lib/ui";
import { Accordion } from "./Accordion";

export interface TripFormValues {
  origin: string;
  destination: string;
  startDate: string;
  endDate: string;
  preferences: string;
  pace: Pace;
  budget: Budget;
  accessibility: boolean;
  interests: string;
  maxDrivingHours: number;
  maxStopsPerDay: number;
  maxReplanAttempts: number;
  maxDetourKm: number;
  maxBacktrackingPercent: number;
  requireProgress: boolean;
  allowedCountries: string;
  allowExtendedStays: boolean;
  maxNightsPerStop: number;
  allowReturnStops: boolean;
  failOnWeatherWarnings: boolean;
  maxPrecipChance: number;
  minTempC: number;
}

function formatInputDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function defaultTripValues(now = new Date()): TripFormValues {
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const end = new Date(start);
  end.setDate(end.getDate() + 5);

  return {
    origin: "San Diego, CA",
    destination: "San Francisco, CA",
    startDate: formatInputDate(start),
    endDate: formatInputDate(end),
    preferences:
      "Coastal drive with time for beaches, a Big Sur overlook, and a meal in a harbor town.",
    pace: "moderate",
    budget: "moderate",
    accessibility: false,
    interests: "beaches, coastal views, state parks, food",
    maxDrivingHours: 6,
    maxStopsPerDay: 4,
    maxReplanAttempts: 2,
    maxDetourKm: 30,
    maxBacktrackingPercent: 15,
    requireProgress: true,
    allowedCountries: "US, MX",
    allowExtendedStays: false,
    maxNightsPerStop: 1,
    allowReturnStops: false,
    failOnWeatherWarnings: false,
    maxPrecipChance: 0.5,
    minTempC: 10,
  };
}

interface TripFormProps {
  disabled?: boolean;
  onSubmit: (payload: TripRequestPayload) => void;
}

const inputClassName = fieldClass;
const labelClassName = "block space-y-1 text-sm";

function buildPayload(values: TripFormValues): TripRequestPayload {
  const interests = parseCommaList(values.interests);
  const allowedCountries = parseCommaList(values.allowedCountries).map((country) =>
    country.toUpperCase(),
  );

  return {
    origin: values.origin.trim(),
    destination: values.destination.trim(),
    start_date: values.startDate,
    end_date: values.endDate,
    preferences: values.preferences.trim() || null,
    structured_preferences: {
      pace: values.pace,
      budget: values.budget,
      accessibility: values.accessibility,
      interests,
    },
    constraints: {
      max_driving_hours_per_day: values.maxDrivingHours,
      max_stops_per_day: values.maxStopsPerDay,
      max_replan_attempts: values.maxReplanAttempts,
      max_detour_km_per_stop: values.maxDetourKm,
      max_backtracking_percent: values.maxBacktrackingPercent,
      require_progress_toward_destination: values.requireProgress,
      allowed_countries: allowedCountries.length > 0 ? allowedCountries : undefined,
      allow_extended_stays: values.allowExtendedStays,
      max_nights_per_stop: values.allowExtendedStays ? values.maxNightsPerStop : 1,
      allow_return_stops: values.allowReturnStops,
      fail_on_weather_warnings: values.failOnWeatherWarnings,
      max_precip_chance: values.maxPrecipChance,
      min_temp_c: values.minTempC,
    },
  };
}

export function createTripPayload(fields: {
  origin: string;
  destination: string;
  startDate: string;
  endDate: string;
}): TripRequestPayload {
  return buildPayload({
    ...defaultTripValues(),
    origin: fields.origin,
    destination: fields.destination,
    startDate: fields.startDate,
    endDate: fields.endDate,
  });
}

export function TripForm({ disabled = false, onSubmit }: TripFormProps) {
  const [values, setValues] = useState<TripFormValues>(() => defaultTripValues());
  const [formError, setFormError] = useState<string | null>(null);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (tripLengthDays(values.startDate, values.endDate) > MAX_TRIP_DAYS) {
      setFormError(`A trip can be at most ${MAX_TRIP_DAYS} days.`);
      return;
    }
    setFormError(null);
    onSubmit(buildPayload(values));
  }

  function updateField<K extends keyof TripFormValues>(key: K, value: TripFormValues[K]) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5 rounded-2xl bg-paper p-6 text-pine shadow-[0_16px_40px_rgb(28_58_46_/_0.06)] ring-1 ring-pine/10 sm:p-7">
      <div>
        <h2 className="font-display text-3xl leading-none tracking-[-0.03em] text-pine">Plan a road trip</h2>
        <p className="mt-3 max-w-prose text-sm leading-relaxed text-pine-muted">
          Submit your route and dates. Planning runs in the background while you watch progress.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className={labelClassName}>
          <span className="font-medium text-pine">Origin</span>
          <input
            required
            maxLength={MAX_LOCATION_LENGTH}
            value={values.origin}
            onChange={(event) => updateField("origin", event.target.value)}
            className={inputClassName}
            placeholder="San Diego, CA"
          />
        </label>
        <label className={labelClassName}>
          <span className="font-medium text-pine">Destination</span>
          <input
            required
            maxLength={MAX_LOCATION_LENGTH}
            value={values.destination}
            onChange={(event) => updateField("destination", event.target.value)}
            className={inputClassName}
            placeholder="San Francisco, CA"
          />
        </label>
        <label className={labelClassName}>
          <span className="font-medium text-pine">Start date</span>
          <input
            required
            type="date"
            value={values.startDate}
            onChange={(event) => updateField("startDate", event.target.value)}
            className={inputClassName}
          />
        </label>
        <label className={labelClassName}>
          <span className="font-medium text-pine">End date</span>
          <input
            required
            type="date"
            value={values.endDate}
            min={values.startDate || undefined}
            max={values.startDate ? addIsoDays(values.startDate, MAX_TRIP_DAYS - 1) : undefined}
            onChange={(event) => updateField("endDate", event.target.value)}
            className={inputClassName}
          />
        </label>
      </div>

      <Accordion title="Structured preferences" description="Pace, budget, accessibility, and interests">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className={labelClassName}>
            <span className="font-medium text-pine">Pace</span>
            <select
              value={values.pace}
              onChange={(event) => updateField("pace", event.target.value as Pace)}
              className={inputClassName}
            >
              <option value="relaxed">Relaxed</option>
              <option value="moderate">Moderate</option>
              <option value="packed">Packed</option>
            </select>
          </label>
          <label className={labelClassName}>
            <span className="font-medium text-pine">Budget</span>
            <select
              value={values.budget}
              onChange={(event) => updateField("budget", event.target.value as Budget)}
              className={inputClassName}
            >
              <option value="budget">Budget</option>
              <option value="moderate">Moderate</option>
              <option value="luxury">Luxury</option>
            </select>
          </label>
        </div>
        <label className={`${labelClassName} mt-4 flex items-center gap-2`}>
          <input
            type="checkbox"
            checked={values.accessibility}
            onChange={(event) => updateField("accessibility", event.target.checked)}
            className="size-4 accent-pine"
          />
          <span className="font-medium text-pine">Prefer accessible venues and routes</span>
        </label>
        <label className={`${labelClassName} mt-4`}>
          <span className="font-medium text-pine">Interests</span>
          <input
            value={values.interests}
            maxLength={MAX_INTERESTS_LENGTH}
            onChange={(event) => updateField("interests", event.target.value)}
            className={inputClassName}
            placeholder="breweries, coastal_views, museums"
          />
          <span className="text-xs text-pine-muted">
            Comma-separated, up to 10 interests, 40 characters each
          </span>
        </label>
      </Accordion>

      <label className={labelClassName}>
        <span className="font-medium text-pine">Additional notes</span>
        <textarea
          value={values.preferences}
          maxLength={MAX_NOTES_LENGTH}
          onChange={(event) => updateField("preferences", event.target.value)}
          className={`${inputClassName} min-h-20`}
          placeholder="Any extra guidance for the planner"
        />
      </label>
      {formError && (
        <p className="text-sm text-clay" role="alert">
          {formError}
        </p>
      )}

      <div>
        <h3 className="font-display text-xl tracking-[-0.02em] text-pine">Core constraints</h3>
        <div className="mt-3 grid gap-4 sm:grid-cols-3">
          <label className={labelClassName}>
            <span className="font-medium text-pine">Max driving hours / day</span>
            <input
              type="number"
              min={1}
              max={8}
              step={0.5}
              value={values.maxDrivingHours}
              onChange={(event) => updateField("maxDrivingHours", Number(event.target.value))}
              className={inputClassName}
            />
          </label>
          <label className={labelClassName}>
            <span className="font-medium text-pine">Max stops / day</span>
            <input
              type="number"
              min={1}
              max={8}
              value={values.maxStopsPerDay}
              onChange={(event) => updateField("maxStopsPerDay", Number(event.target.value))}
              className={inputClassName}
            />
          </label>
          <label className={labelClassName}>
            <span className="font-medium text-pine">Max replan attempts</span>
            <input
              type="number"
              min={0}
              max={5}
              value={values.maxReplanAttempts}
              onChange={(event) => updateField("maxReplanAttempts", Number(event.target.value))}
              className={inputClassName}
            />
          </label>
        </div>
      </div>

      <Accordion
        title="Advanced constraints"
        description="Routing, stays, countries, and weather thresholds"
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <label className={labelClassName}>
            <span className="font-medium text-pine">Max detour km / stop</span>
            <input
              type="number"
              min={0}
              max={100}
              step={1}
              value={values.maxDetourKm}
              onChange={(event) => updateField("maxDetourKm", Number(event.target.value))}
              className={inputClassName}
            />
          </label>
          <label className={labelClassName}>
            <span className="font-medium text-pine">Max backtracking %</span>
            <input
              type="number"
              min={0}
              max={50}
              step={1}
              value={values.maxBacktrackingPercent}
              onChange={(event) => updateField("maxBacktrackingPercent", Number(event.target.value))}
              className={inputClassName}
            />
            {values.allowReturnStops && (
              <span className="text-xs text-pine-muted">Clamped to 25% when return stops are enabled</span>
            )}
          </label>
          <label className={labelClassName}>
            <span className="font-medium text-pine">Allowed countries</span>
            <input
              value={values.allowedCountries}
              onChange={(event) => updateField("allowedCountries", event.target.value)}
              className={inputClassName}
              placeholder="US, MX"
            />
          </label>
          <label className={labelClassName}>
            <span className="font-medium text-pine">Max nights / stop</span>
            <input
              type="number"
              min={1}
              max={7}
              value={values.maxNightsPerStop}
              disabled={!values.allowExtendedStays}
              onChange={(event) => updateField("maxNightsPerStop", Number(event.target.value))}
              className={inputClassName}
            />
          </label>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="flex items-center gap-2 text-sm text-pine">
            <input
              type="checkbox"
              checked={values.requireProgress}
              disabled={values.allowReturnStops}
              onChange={(event) => updateField("requireProgress", event.target.checked)}
              className="size-4 accent-pine"
            />
            Require progress toward destination
          </label>
          <label className="flex items-center gap-2 text-sm text-pine">
            <input
              type="checkbox"
              checked={values.allowExtendedStays}
              onChange={(event) => updateField("allowExtendedStays", event.target.checked)}
              className="size-4 accent-pine"
            />
            Allow extended stays
          </label>
          <label className="flex items-center gap-2 text-sm text-pine">
            <input
              type="checkbox"
              checked={values.allowReturnStops}
              onChange={(event) => updateField("allowReturnStops", event.target.checked)}
              className="size-4 accent-pine"
            />
            Allow return stops
          </label>
          <label className="flex items-center gap-2 text-sm text-pine">
            <input
              type="checkbox"
              checked={values.failOnWeatherWarnings}
              onChange={(event) => updateField("failOnWeatherWarnings", event.target.checked)}
              className="size-4 accent-pine"
            />
            Fail on weather warnings
          </label>
        </div>

        {values.failOnWeatherWarnings && (
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <label className={labelClassName}>
              <span className="font-medium text-pine">Max precipitation chance</span>
              <input
                type="number"
                min={0}
                max={1}
                step={0.05}
                value={values.maxPrecipChance}
                onChange={(event) => updateField("maxPrecipChance", Number(event.target.value))}
                className={inputClassName}
              />
            </label>
            <label className={labelClassName}>
              <span className="font-medium text-pine">Min temp (°C)</span>
              <input
                type="number"
                min={-30}
                max={40}
                step={1}
                value={values.minTempC}
                onChange={(event) => updateField("minTempC", Number(event.target.value))}
                className={inputClassName}
              />
            </label>
          </div>
        )}
      </Accordion>

      <button
        type="submit"
        disabled={disabled}
        className={`${primaryButtonClass} w-full sm:w-auto`}
      >
        {disabled ? "Planning..." : "Start planning"}
      </button>
    </form>
  );
}
