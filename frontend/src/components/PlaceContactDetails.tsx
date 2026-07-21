import type { PlaceContact } from "../api/client";

interface PlaceContactDetailsProps {
  contact?: PlaceContact;
}

export function PlaceContactDetails({ contact }: PlaceContactDetailsProps) {
  if (!contact) {
    return null;
  }

  const hasDetails =
    contact.phone || contact.website || contact.address || contact.opening_hours;

  if (!hasDetails && !contact.reservation_required) {
    return null;
  }

  return (
    <div className="mt-2 space-y-1 text-xs text-slate-600">
      {contact.address && <p>{contact.address}</p>}
      {contact.opening_hours && <p>Hours: {contact.opening_hours}</p>}
      {contact.phone && (
        <p>
          <a className="text-blue-700 hover:underline" href={`tel:${contact.phone}`}>
            {contact.phone}
          </a>
        </p>
      )}
      {contact.website && (
        <p>
          <a
            className="text-blue-700 hover:underline"
            href={contact.website}
            rel="noreferrer"
            target="_blank"
          >
            Website
          </a>
        </p>
      )}
      {contact.reservation_required && (
        <p className="font-medium text-amber-700">Reservation recommended</p>
      )}
    </div>
  );
}
