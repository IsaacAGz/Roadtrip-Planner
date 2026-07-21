import type { FormEvent } from "react";
import { useState } from "react";
import type { TripRequestPayload } from "../api/client";
import type { Budget, Pace } from "../lib/tripPayload";
import { parseCommaList } from "../lib/tripPayload";
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

const defaultValues: TripFormValues = {
  origin: "San Jose, CA",
  destination: "Monterey, CA",
  startDate: "2026-07-15",
  endDate: "2026-07-15",
  preferences: "direct route, minimal stops",
  pace: "moderate",
  budget: "moderate",
  accessibility: false,
  interests: "coastal_views, breweries",
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

interface TripFormProps {
  disabled?: boolean;
  onSubmit: (payload: TripRequestPayload) => void;
}

const inputClassName = "w-full rounded-lg border border-slate-300 px-3 py-2";
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

export function TripForm({ disabled = false, onSubmit }: TripFormProps) {
  const [values, setValues] = useState<TripFormValues>(defaultValues);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit(buildPayload(values));
  }

  function updateField<K extends keyof TripFormValues>(key: K, value: TripFormValues[K]) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Plan a road trip</h2>
        <p className="mt-1 text-sm text-slate-600">
          Submit your route and dates. Planning runs in the background while you watch progress.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className={labelClassName}>
          <span className="font-medium text-slate-700">Origin</span>
          <input
            required
            value={values.origin}
            onChange={(event) => updateField("origin", event.target.value)}
            className={inputClassName}
            placeholder="San Jose, CA"
          />
        </label>
        <label className={labelClassName}>
          <span className="font-medium text-slate-700">Destination</span>
          <input
            required
            value={values.destination}
            onChange={(event) => updateField("destination", event.target.value)}
            className={inputClassName}
            placeholder="Monterey, CA"
          />
        </label>
        <label className={labelClassName}>
          <span className="font-medium text-slate-700">Start date</span>
          <input
            required
            type="date"
            value={values.startDate}
            onChange={(event) => updateField("startDate", event.target.value)}
            className={inputClassName}
          />
        </label>
        <label className={labelClassName}>
          <span className="font-medium text-slate-700">End date</span>
          <input
            required
            type="date"
            value={values.endDate}
            onChange={(event) => updateField("endDate", event.target.value)}
            className={inputClassName}
          />
        </label>
      </div>

      <Accordion title="Structured preferences" description="Pace, budget, accessibility, and interests">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className={labelClassName}>
            <span className="font-medium text-slate-700">Pace</span>
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
            <span className="font-medium text-slate-700">Budget</span>
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
            className="h-4 w-4 rounded border-slate-300"
          />
          <span className="font-medium text-slate-700">Prefer accessible venues and routes</span>
        </label>
        <label className={`${labelClassName} mt-4`}>
          <span className="font-medium text-slate-700">Interests</span>
          <input
            value={values.interests}
            onChange={(event) => updateField("interests", event.target.value)}
            className={inputClassName}
            placeholder="breweries, coastal_views, museums"
          />
          <span className="text-xs text-slate-500">Comma-separated, up to 10 interests</span>
        </label>
      </Accordion>

      <label className={labelClassName}>
        <span className="font-medium text-slate-700">Additional notes</span>
        <textarea
          value={values.preferences}
          onChange={(event) => updateField("preferences", event.target.value)}
          className="min-h-20 w-full rounded-lg border border-slate-300 px-3 py-2"
          placeholder="Any extra guidance for the planner"
        />
      </label>

      <div>
        <h3 className="text-sm font-semibold text-slate-900">Core constraints</h3>
        <div className="mt-3 grid gap-4 sm:grid-cols-3">
          <label className={labelClassName}>
            <span className="font-medium text-slate-700">Max driving hours / day</span>
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
            <span className="font-medium text-slate-700">Max stops / day</span>
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
            <span className="font-medium text-slate-700">Max replan attempts</span>
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
            <span className="font-medium text-slate-700">Max detour km / stop</span>
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
            <span className="font-medium text-slate-700">Max backtracking %</span>
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
              <span className="text-xs text-slate-500">Clamped to 25% when return stops are enabled</span>
            )}
          </label>
          <label className={labelClassName}>
            <span className="font-medium text-slate-700">Allowed countries</span>
            <input
              value={values.allowedCountries}
              onChange={(event) => updateField("allowedCountries", event.target.value)}
              className={inputClassName}
              placeholder="US, MX"
            />
          </label>
          <label className={labelClassName}>
            <span className="font-medium text-slate-700">Max nights / stop</span>
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
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={values.requireProgress}
              disabled={values.allowReturnStops}
              onChange={(event) => updateField("requireProgress", event.target.checked)}
              className="h-4 w-4 rounded border-slate-300"
            />
            Require progress toward destination
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={values.allowExtendedStays}
              onChange={(event) => updateField("allowExtendedStays", event.target.checked)}
              className="h-4 w-4 rounded border-slate-300"
            />
            Allow extended stays
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={values.allowReturnStops}
              onChange={(event) => updateField("allowReturnStops", event.target.checked)}
              className="h-4 w-4 rounded border-slate-300"
            />
            Allow return stops
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={values.failOnWeatherWarnings}
              onChange={(event) => updateField("failOnWeatherWarnings", event.target.checked)}
              className="h-4 w-4 rounded border-slate-300"
            />
            Fail on weather warnings
          </label>
        </div>

        {values.failOnWeatherWarnings && (
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <label className={labelClassName}>
              <span className="font-medium text-slate-700">Max precipitation chance</span>
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
              <span className="font-medium text-slate-700">Min temp (°C)</span>
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
        className="w-full rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400 sm:w-auto"
      >
        {disabled ? "Planning..." : "Start planning"}
      </button>
    </form>
  );
}
