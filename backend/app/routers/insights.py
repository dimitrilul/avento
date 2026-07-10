from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..ai import period_review_data_basis, period_review_summary
from ..analysis import personal_records
from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..models import Activity, User, utcnow
from ..schemas import LongTermInsightsResponse, PeriodReviewResponse, PersonalRecordsResponse
from ..statistics import build_long_term_insights


router = APIRouter(tags=["Insights"])


def _local_midnight(value: date, timezone_name: str) -> datetime:
    return datetime.combine(value, time.min, tzinfo=ZoneInfo(timezone_name)).astimezone(timezone.utc)


def _local_date(value: datetime, timezone_name: str) -> date:
    aware = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return aware.astimezone(ZoneInfo(timezone_name)).date()


def _validated_period(
    db: Session,
    user: User,
    date_from: date | None,
    date_to: date | None,
) -> tuple[date, date]:
    timezone_name = get_settings().timezone
    end = date_to or datetime.now(ZoneInfo(timezone_name)).date()
    if end.year >= 9999:
        raise HTTPException(status_code=422, detail="Das Enddatum liegt außerhalb des unterstützten Bereichs.")
    start = date_from
    if start is None:
        earliest = db.scalar(
            select(func.min(Activity.started_at)).where(
                Activity.user_id == user.id,
                Activity.started_at < _local_midnight(end + timedelta(days=1), timezone_name),
            )
        )
        start = _local_date(earliest, timezone_name) if earliest else end
    if start < date(1900, 1, 1):
        raise HTTPException(status_code=422, detail="Insight-Zeiträume vor 1900 werden nicht unterstützt.")
    if end < start:
        raise HTTPException(status_code=422, detail="Das Enddatum muss am oder nach dem Startdatum liegen.")
    if (end - start).days + 1 > 36_525:
        raise HTTPException(status_code=422, detail="Der Insight-Zeitraum darf höchstens 100 Jahre umfassen.")
    return start, end


def _activities_in_period(db: Session, user: User, start: date, end: date) -> list[Activity]:
    timezone_name = get_settings().timezone
    return list(
        db.scalars(
            select(Activity)
            .where(
                Activity.user_id == user.id,
                Activity.started_at >= _local_midnight(start, timezone_name),
                Activity.started_at < _local_midnight(end + timedelta(days=1), timezone_name),
            )
            .order_by(Activity.started_at)
        ).all()
    )


@router.get("/statistics/records", response_model=PersonalRecordsResponse)
def get_personal_records(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PersonalRecordsResponse:
    activities = list(
        db.scalars(
            select(Activity).where(Activity.user_id == current_user.id).order_by(Activity.started_at)
        ).all()
    )
    records = personal_records(activities)
    return PersonalRecordsResponse(
        generated_at=utcnow(),
        **records,
        methods=[
            {
                "name": "distance_record_track_points",
                "description": "Schnellster zusammenhängender Distanzabschnitt mit linearer Interpolation an den Abschnittsgrenzen.",
                "parameters": {"target_distances_m": [10_000, 20_000, 30_000, 40_000, 50_000], "time_basis": "elapsed"},
            },
            {
                "name": "distance_record_fallback",
                "description": "Nur ohne ausreichende Trackpunkte wird die Zeit aus dem Aktivitätsdurchschnitt geschätzt und markiert.",
                "parameters": {"estimated": True},
            },
        ],
    )


@router.get("/statistics/insights", response_model=LongTermInsightsResponse)
def get_long_term_insights(
    date_from: date | None = None,
    date_to: date | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LongTermInsightsResponse:
    start, end = _validated_period(db, current_user, date_from, date_to)
    span = (end - start).days + 1
    previous_to = start - timedelta(days=1)
    previous_from = previous_to - timedelta(days=span - 1)
    activities = _activities_in_period(db, current_user, start, end)
    previous = _activities_in_period(db, current_user, previous_from, previous_to)
    result = build_long_term_insights(
        activities,
        previous,
        start,
        end,
        previous_from,
        previous_to,
        get_settings().timezone,
    )
    return LongTermInsightsResponse(
        generated_at=utcnow(),
        **result,
        methods=[
            {
                "name": "calendar_comparison",
                "description": "Monats- und Jahreswerte nach lokalem Kalender sowie Vergleich mit dem unmittelbar vorherigen gleich langen Zeitraum.",
                "parameters": {"timezone": get_settings().timezone, "previous_period_days": span},
            },
            {
                "name": "robust_association",
                "description": "Wetter- und Tempomuster nur bei ausreichender Stichprobe und übereinstimmendem Rang- und Medianeffekt.",
                "parameters": {"minimum_sample": 8, "minimum_absolute_spearman": 0.35, "minimum_effect_percent": 4},
            },
            {
                "name": "fitness_and_recovery_trend",
                "description": "Medianvergleich chronologischer Drittel sowie Aktivitätsabstände von höchstens 36 und mindestens 60 Stunden.",
                "parameters": {"minimum_fitness_sample": 6, "minimum_recovery_group": 3},
            },
        ],
        disclaimer=(
            "Die Insights beschreiben Zusammenhänge in aufgezeichneten Trainingsdaten. Sie belegen keine Ursache, "
            "ersetzen keine medizinische Einschätzung und können durch Streckenwahl, Wetter und Sensorlücken beeinflusst sein."
        ),
    )


def _review_period(year: int, season: str) -> tuple[date, date, str]:
    if season == "year":
        return date(year, 1, 1), date(year, 12, 31), f"Im Jahr {year}"
    if season == "winter":
        return date(year - 1, 12, 1), date(year, 2, 28 + calendar_is_leap(year)), f"Im Winter {year}"
    ranges = {
        "spring": (3, 5, "Frühling"),
        "summer": (6, 8, "Sommer"),
        "autumn": (9, 11, "Herbst"),
    }
    start_month, end_month, label = ranges[season]
    end_day = 30 if end_month in {4, 6, 9, 11} else 31
    return date(year, start_month, 1), date(year, end_month, end_day), f"Im {label} {year}"


def calendar_is_leap(year: int) -> int:
    return int(year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))


@router.get("/statistics/reviews/{year}", response_model=PeriodReviewResponse)
def get_period_review(
    year: int,
    season: str = Query(default="year", pattern=r"^(year|winter|spring|summer|autumn)$"),
    use_openai: bool = Query(default=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PeriodReviewResponse:
    if year < 1901 or year > 9998:
        raise HTTPException(status_code=422, detail="Das Rückblickjahr muss zwischen 1901 und 9998 liegen.")
    start, end, label = _review_period(year, season)
    activities = _activities_in_period(db, current_user, start, end)
    span = (end - start).days + 1
    previous_to = start - timedelta(days=1)
    previous_from = previous_to - timedelta(days=span - 1)
    previous = _activities_in_period(db, current_user, previous_from, previous_to)
    insights = build_long_term_insights(
        activities,
        previous,
        start,
        end,
        previous_from,
        previous_to,
        get_settings().timezone,
    )
    records = personal_records(activities)
    facts = jsonable_encoder(
        {
            "label": label,
            "period": {"date_from": start, "date_to": end, "timezone": get_settings().timezone},
            "totals": insights["current"],
            "previous_period": insights["previous_period"],
            "changes_from_previous_period": insights["changes"],
            "monthly": insights["monthly"],
            "yearly": insights["yearly"],
            "fitness_trend": insights["fitness_trend"],
            "patterns": insights["patterns"],
            "records": records,
        }
    )
    summary, provider = period_review_summary(get_settings(), facts, use_openai=use_openai)
    period_start = _local_midnight(start, get_settings().timezone)
    period_end = _local_midnight(end + timedelta(days=1), get_settings().timezone) - timedelta(microseconds=1)
    data_basis = period_review_data_basis(
        facts,
        [activity.id for activity in activities],
        period_start,
        period_end,
        get_settings().timezone,
        provider,
    )
    return PeriodReviewResponse(
        year=year,
        season=season,
        period={"date_from": start, "date_to": end},
        summary=summary,
        provider=provider,
        generated_at=utcnow(),
        data_basis=data_basis,
    )
