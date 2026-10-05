export type Pace = "relaxed" | "moderate" | "packed";
export type Budget = "budget" | "moderate" | "luxury";

export interface TripPreferences {
  pace: Pace;
  budget: Budget;
  accessibility: boolean;
  interests: string[];
}

export interface TripConstraints {
  max_driving_hours_per_day?: number;
  max_stops_per_day?: number;
  max_detour_km_per_stop?: number;
  max_backtracking_percent?: number;
  require_progress_toward_destination?: boolean;
  allowed_countries?: string[];
  allow_extended_stays?: boolean;
  max_nights_per_stop?: number;
  allow_return_stops?: boolean;
  max_replan_attempts?: number;
  fail_on_weather_warnings?: boolean;
  max_precip_chance?: number;
  min_temp_c?: number;
}

export interface TripRequestPayload {
  origin: string;
  destination: string;
  start_date: string;
  end_date: string;
  preferences?: string | null;
  structured_preferences?: TripPreferences;
  constraints?: TripConstraints;
}

export const MAX_TRIP_DAYS = 14;
export const MAX_LOCATION_LENGTH = 120;
export const MAX_NOTES_LENGTH = 1000;
export const MAX_INTERESTS_LENGTH = 500;

export function addIsoDays(isoDate: string, days: number): string {
  const date = new Date(`${isoDate}T00:00:00`);
  date.setDate(date.getDate() + days);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function tripLengthDays(startDate: string, endDate: string): number {
  const start = new Date(`${startDate}T00:00:00`);
  const end = new Date(`${endDate}T00:00:00`);
  return Math.round((end.getTime() - start.getTime()) / 86_400_000) + 1;
}

export function parseCommaList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function joinCommaList(values: string[]): string {
  return values.join(", ");
}
