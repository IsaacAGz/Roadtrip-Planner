from app.models.itinerary import RoadtripPlan
from app.models.trip import TripRequest
from app.models.validation import ValidationReport
from app.validators.driving import validate_driving
from app.validators.geography import validate_geography
from app.validators.poi import validate_poi
from app.validators.routing import validate_routing
from app.validators.structure import validate_structure
from app.validators.warnings import collect_warnings


async def run_hard_validators(plan: RoadtripPlan, request: TripRequest) -> ValidationReport:
    constraints = request.constraints
    failures: list = []
    warnings: list = []

    failures.extend(validate_structure(plan, request, constraints))
    failures.extend(validate_geography(plan, constraints))
    failures.extend(validate_poi(plan, constraints))
    failures.extend(await validate_driving(plan, constraints))
    failures.extend(await validate_routing(plan, constraints))
    warnings.extend(await collect_warnings(plan, constraints))

    return ValidationReport(
        approved=len(failures) == 0,
        hard_failures=failures,
        warnings=warnings,
    )
