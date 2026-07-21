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

export function parseCommaList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function joinCommaList(values: string[]): string {
  return values.join(", ");
}
