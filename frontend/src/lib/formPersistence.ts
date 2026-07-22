import type { TripRequestPayload } from "../api/client";
import type { TripFormValues } from "../components/TripForm";
import { parseCommaList } from "./tripPayload";

const DRAFT_STORAGE_KEY = "roadtrip-planner.form-draft";

export function loadFormDraft(): TripFormValues | null {
  try {
    const raw = sessionStorage.getItem(DRAFT_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    return JSON.parse(raw) as TripFormValues;
  } catch {
    return null;
  }
}

export function saveFormDraft(values: TripFormValues): void {
  sessionStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(values));
}

export function payloadToFormValues(payload: TripRequestPayload): TripFormValues {
  const constraints = payload.constraints ?? {};
  const prefs = payload.structured_preferences;

  return {
    origin: payload.origin,
    destination: payload.destination,
    startDate: payload.start_date,
    endDate: payload.end_date,
    preferences: payload.preferences ?? "",
    pace: prefs?.pace ?? "moderate",
    budget: prefs?.budget ?? "moderate",
    accessibility: prefs?.accessibility ?? false,
    interests: (prefs?.interests ?? []).join(", "),
    maxDrivingHours: constraints.max_driving_hours_per_day ?? 6,
    maxStopsPerDay: constraints.max_stops_per_day ?? 4,
    maxReplanAttempts: constraints.max_replan_attempts ?? 2,
    maxDetourKm: constraints.max_detour_km_per_stop ?? 30,
    maxBacktrackingPercent: constraints.max_backtracking_percent ?? 15,
    requireProgress: constraints.require_progress_toward_destination ?? true,
    allowedCountries: (constraints.allowed_countries ?? ["US", "MX"]).join(", "),
    allowExtendedStays: constraints.allow_extended_stays ?? false,
    maxNightsPerStop: constraints.max_nights_per_stop ?? 1,
    allowReturnStops: constraints.allow_return_stops ?? false,
    failOnWeatherWarnings: constraints.fail_on_weather_warnings ?? false,
    maxPrecipChance: constraints.max_precip_chance ?? 0.5,
    minTempC: constraints.min_temp_c ?? 10,
  };
}

export function formValuesToPayload(values: TripFormValues): TripRequestPayload {
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
