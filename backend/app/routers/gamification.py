from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..gamification import (
    BADGE_DEFINITIONS,
    DISCOVERY_KINDS,
    GamificationActivityNotFoundError,
    GamificationUserNotFoundError,
    METRIC_UNITS,
    SUPPORTED_METRICS,
    annual_award_payloads,
    badge_payloads,
    build_snapshot,
    challenge_payload,
    discovery_summary_payload,
    goal_payload,
    goal_period_bounds,
    level_for_xp,
    total_xp,
)
from ..gamification_ai import ai_challenges_available, generate_challenge_suggestions
from ..geography import reverse_geocode_track
from ..models import GamificationChallenge, GamificationGoal, User, utcnow, uuid4_str
from ..schemas import (
    GamificationAnnualAwardListResponse,
    GamificationBadgeListResponse,
    GamificationChallengeAccept,
    GamificationChallengeCreate,
    GamificationChallengeListResponse,
    GamificationChallengeResponse,
    GamificationChallengeUpdate,
    GamificationDiscoveryListResponse,
    GamificationDiscoveryResponse,
    GamificationGoalCreate,
    GamificationGoalListResponse,
    GamificationGoalResponse,
    GamificationGoalUpdate,
    GamificationOverviewResponse,
    GamificationRecordChaseResponse,
)


router = APIRouter(prefix="/gamification", tags=["Gamification"])


def _today() -> date:
    from zoneinfo import ZoneInfo

    return utcnow().astimezone(ZoneInfo(get_settings().timezone)).date()


def _snapshot(db: Session, user: User):
    settings = get_settings()
    snapshot = build_snapshot(db, user, settings.timezone, _today())
    if settings.openai_api_key:
        has_ai_suggestions = any(item.source == "ai" and item.status == "suggested" for item in snapshot.challenges)
        if not has_ai_suggestions:
            try:
                suggestions = generate_challenge_suggestions(settings, user, snapshot.activities)
                if suggestions:
                    from ..gamification import upsert_challenge_suggestions

                    upsert_challenge_suggestions(db, user.id, suggestions)
                    snapshot = build_snapshot(db, user, settings.timezone, _today())
            except Exception:
                # AI is an optional enhancement. The deterministic private
                # gamification system remains fully usable when it fails.
                pass
    return snapshot


def _goal_response(db: Session, user: User, goal: GamificationGoal) -> GamificationGoalResponse:
    snapshot = build_snapshot(db, user, get_settings().timezone, _today())
    return GamificationGoalResponse.model_validate(goal_payload(goal, snapshot))


def _challenge_response(db: Session, user: User, challenge: GamificationChallenge) -> GamificationChallengeResponse:
    snapshot = build_snapshot(db, user, get_settings().timezone, _today())
    return GamificationChallengeResponse.model_validate(challenge_payload(challenge, snapshot))


def _goal_for_user(db: Session, user: User, goal_id: str) -> GamificationGoal:
    goal = db.scalar(select(GamificationGoal).where(GamificationGoal.id == goal_id, GamificationGoal.user_id == user.id))
    if goal is None:
        raise HTTPException(status_code=404, detail="Ziel nicht gefunden.")
    return goal


def _challenge_for_user(db: Session, user: User, challenge_id: str) -> GamificationChallenge:
    challenge = db.scalar(
        select(GamificationChallenge).where(
            GamificationChallenge.id == challenge_id,
            GamificationChallenge.user_id == user.id,
        )
    )
    if challenge is None:
        raise HTTPException(status_code=404, detail="Challenge nicht gefunden.")
    return challenge


@router.get("/overview", response_model=GamificationOverviewResponse)
def overview(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GamificationOverviewResponse:
    snapshot = _snapshot(db, current_user)
    total, breakdown = total_xp(snapshot)
    active = [challenge_payload(item, snapshot) for item in snapshot.challenges if item.status in {"accepted", "completed"}]
    suggestions = [challenge_payload(item, snapshot) for item in snapshot.challenges if item.status == "suggested"]
    response = GamificationOverviewResponse(
        generated_at=snapshot.generated_at,
        privacy="private",
        level=level_for_xp(total, breakdown),
        goals=[goal_payload(goal, snapshot) for goal in snapshot.goals],
        active_challenges=active,
        challenge_suggestions=suggestions,
        ai_challenges_available=ai_challenges_available(get_settings()),
        badges=badge_payloads(snapshot),
        streak=snapshot.streak,
        record_chases=snapshot_record_chases(snapshot),
        discoveries=discovery_summary_payload(snapshot.discoveries),
        annual_awards=annual_award_payloads(snapshot),
    )
    db.commit()
    return response


def snapshot_record_chases(snapshot: Any) -> list[GamificationRecordChaseResponse]:
    from ..gamification import _record_chases

    return [GamificationRecordChaseResponse.model_validate(item) for item in _record_chases(snapshot.activities)]


@router.get("/goals", response_model=GamificationGoalListResponse)
def list_goals(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GamificationGoalListResponse:
    snapshot = _snapshot(db, current_user)
    goals = [goal_payload(goal, snapshot) for goal in snapshot.goals]
    db.commit()
    return GamificationGoalListResponse(items=goals, total=len(goals))


@router.post("/goals", response_model=GamificationGoalResponse, status_code=status.HTTP_201_CREATED)
def create_goal(payload: GamificationGoalCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GamificationGoalResponse:
    starts_on, deadline = goal_period_bounds(payload.period, _today(), payload.starts_at, payload.deadline)
    goal = GamificationGoal(
        user_id=current_user.id,
        title=payload.title,
        description=payload.description,
        metric=payload.metric,
        target_value=payload.target_value,
        period=payload.period,
        starts_on=starts_on,
        deadline=deadline,
        status="active",
        reward_xp=100,
    )
    db.add(goal)
    db.flush()
    snapshot = _snapshot(db, current_user)
    db.commit()
    return GamificationGoalResponse.model_validate(goal_payload(goal, snapshot))


@router.patch("/goals/{goal_id}", response_model=GamificationGoalResponse)
def update_goal(
    goal_id: str,
    payload: GamificationGoalUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GamificationGoalResponse:
    goal = _goal_for_user(db, current_user, goal_id)
    values = payload.model_dump(exclude_unset=True)
    for key, value in values.items():
        if key == "starts_at":
            goal.starts_on = value
        elif hasattr(goal, key):
            setattr(goal, key, value)
    if goal.starts_on and goal.deadline and goal.deadline < goal.starts_on:
        raise HTTPException(status_code=422, detail="Das Enddatum muss am oder nach dem Startdatum liegen.")
    if goal.status == "completed" and values.get("status") == "active":
        goal.completed_at = None
    snapshot = _snapshot(db, current_user)
    db.commit()
    return GamificationGoalResponse.model_validate(goal_payload(goal, snapshot))


@router.delete("/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(goal_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    goal = _goal_for_user(db, current_user, goal_id)
    db.delete(goal)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/challenges", response_model=GamificationChallengeListResponse)
def list_challenges(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GamificationChallengeListResponse:
    snapshot = _snapshot(db, current_user)
    items = [challenge_payload(item, snapshot) for item in snapshot.challenges]
    db.commit()
    return GamificationChallengeListResponse(items=items, total=len(items), ai_challenges_available=ai_challenges_available(get_settings()))


@router.post("/challenges", response_model=GamificationChallengeResponse, status_code=status.HTTP_201_CREATED)
def create_challenge(payload: GamificationChallengeCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GamificationChallengeResponse:
    challenge = GamificationChallenge(
        user_id=current_user.id,
        template_key=f"user:{uuid4_str()}",
        title=payload.title,
        description=payload.description,
        metric=payload.metric,
        target_value=payload.target_value,
        duration_days=payload.duration_days,
        weather_sensitive=payload.weather_sensitive,
        safety_note=payload.safety_note,
        source="user",
        status="suggested",
        reward_xp=150,
    )
    db.add(challenge)
    db.flush()
    snapshot = _snapshot(db, current_user)
    db.commit()
    return GamificationChallengeResponse.model_validate(challenge_payload(challenge, snapshot))


@router.patch("/challenges/{challenge_id}", response_model=GamificationChallengeResponse)
def update_challenge(
    challenge_id: str,
    payload: GamificationChallengeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GamificationChallengeResponse:
    challenge = _challenge_for_user(db, current_user, challenge_id)
    if challenge.status not in {"suggested", "accepted"}:
        raise HTTPException(status_code=409, detail="Diese Challenge kann nicht mehr geändert werden.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        if hasattr(challenge, key):
            setattr(challenge, key, value)
    snapshot = _snapshot(db, current_user)
    db.commit()
    return GamificationChallengeResponse.model_validate(challenge_payload(challenge, snapshot))


@router.post("/challenges/{challenge_id}/accept", response_model=GamificationChallengeResponse)
def accept_challenge(
    challenge_id: str,
    payload: GamificationChallengeAccept | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GamificationChallengeResponse:
    challenge = _challenge_for_user(db, current_user, challenge_id)
    if challenge.status != "suggested":
        raise HTTPException(status_code=409, detail="Diese Challenge ist nicht mehr verfügbar.")
    starts_at = (payload.starts_at if payload else None) or _today()
    challenge.starts_on = starts_at
    challenge.expires_on = starts_at + timedelta(days=challenge.duration_days - 1)
    challenge.accepted_at = utcnow()
    challenge.status = "accepted"
    snapshot = _snapshot(db, current_user)
    db.commit()
    return GamificationChallengeResponse.model_validate(challenge_payload(challenge, snapshot))


@router.post("/challenges/{challenge_id}/decline", response_model=GamificationChallengeResponse)
def decline_challenge(challenge_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GamificationChallengeResponse:
    challenge = _challenge_for_user(db, current_user, challenge_id)
    if challenge.status != "suggested":
        raise HTTPException(status_code=409, detail="Diese Challenge ist nicht mehr verfügbar.")
    challenge.status = "declined"
    snapshot = _snapshot(db, current_user)
    db.commit()
    return GamificationChallengeResponse.model_validate(challenge_payload(challenge, snapshot))


@router.post("/challenges/ai-suggestions", response_model=GamificationChallengeListResponse)
def refresh_ai_suggestions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GamificationChallengeListResponse:
    settings = get_settings()
    if not settings.openai_api_key:
        raise HTTPException(status_code=404, detail="KI-Challenge-Vorschläge sind ohne OpenAI-Schlüssel nicht verfügbar.")
    snapshot = build_snapshot(db, current_user, settings.timezone, _today())
    try:
        suggestions = generate_challenge_suggestions(settings, current_user, snapshot.activities)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="KI-Challenge-Vorschläge konnten gerade nicht erstellt werden.") from exc
    from ..gamification import upsert_challenge_suggestions

    upsert_challenge_suggestions(db, current_user.id, suggestions)
    snapshot = build_snapshot(db, current_user, settings.timezone, _today())
    items = [challenge_payload(item, snapshot) for item in snapshot.challenges if item.status == "suggested"]
    db.commit()
    return GamificationChallengeListResponse(items=items, total=len(items), ai_challenges_available=True)


@router.get("/badges", response_model=GamificationBadgeListResponse)
def list_badges(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GamificationBadgeListResponse:
    snapshot = _snapshot(db, current_user)
    items = badge_payloads(snapshot)
    db.commit()
    return GamificationBadgeListResponse(items=items, total=len(items), unlocked=sum(1 for item in items if item["unlocked"]))


@router.get("/discoveries", response_model=GamificationDiscoveryListResponse)
def list_discoveries(
    scope: str | None = Query(default=None, max_length=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GamificationDiscoveryListResponse:
    if scope and scope not in DISCOVERY_KINDS:
        raise HTTPException(status_code=422, detail="Unbekannte Entdeckungskategorie.")
    snapshot = _snapshot(db, current_user)
    selected = [item for item in snapshot.discoveries if scope is None or item.kind == scope]
    items = [GamificationDiscoveryResponse.model_validate({
        "id": item.id, "kind": item.kind, "name": item.name, "region": item.region,
        "country_code": item.country_code, "latitude": item.latitude, "longitude": item.longitude,
        "first_discovered_at": item.first_discovered_at, "first_activity_id": item.first_activity_id,
    }) for item in selected]
    db.commit()
    return GamificationDiscoveryListResponse(items=items, total=len(items), by_scope=discovery_summary_payload(snapshot.discoveries))


@router.post("/discoveries/backfill", response_model=GamificationDiscoveryListResponse)
def backfill_discoveries(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GamificationDiscoveryListResponse:
    """Explicitly geocode existing rides when the owner configured a provider."""

    settings = get_settings()
    if settings.reverse_geocoding_provider.casefold() == "disabled" or not settings.reverse_geocoding_base_url:
        raise HTTPException(status_code=404, detail="Ortsentdeckungen sind ohne ausdrücklich konfigurierten Geocoder nicht verfügbar.")
    from ..gamification import replace_activity_discoveries
    from ..models import Activity

    activities = list(db.scalars(select(Activity).where(Activity.user_id == current_user.id).order_by(Activity.started_at)).all())
    for activity in activities:
        places = reverse_geocode_track(activity.track_points or [], settings)
        if places:
            activity.weather = dict(activity.weather or {})
            activity.weather["route_places"] = places
            replace_activity_discoveries(db, current_user.id, activity.id, places)
    snapshot = build_snapshot(db, current_user, settings.timezone, _today())
    items = [GamificationDiscoveryResponse.model_validate({
        "id": item.id, "kind": item.kind, "name": item.name, "region": item.region,
        "country_code": item.country_code, "latitude": item.latitude, "longitude": item.longitude,
        "first_discovered_at": item.first_discovered_at, "first_activity_id": item.first_activity_id,
    }) for item in snapshot.discoveries]
    db.commit()
    return GamificationDiscoveryListResponse(items=items, total=len(items), by_scope=discovery_summary_payload(snapshot.discoveries))


@router.get("/annual-awards", response_model=GamificationAnnualAwardListResponse)
def list_annual_awards(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GamificationAnnualAwardListResponse:
    snapshot = _snapshot(db, current_user)
    items = annual_award_payloads(snapshot)
    db.commit()
    return GamificationAnnualAwardListResponse(items=items, total=len(items), years=sorted({item["year"] for item in items}, reverse=True))


@router.post("/rebuild", response_model=GamificationOverviewResponse)
def rebuild(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GamificationOverviewResponse:
    # This endpoint is deliberately local-only: it rebuilds derived state from
    # stored activities and never invokes reverse geocoding or an AI provider.
    snapshot = build_snapshot(db, current_user, get_settings().timezone, _today())
    total, breakdown = total_xp(snapshot)
    response = GamificationOverviewResponse(
        generated_at=snapshot.generated_at,
        privacy="private",
        level=level_for_xp(total, breakdown),
        goals=[goal_payload(goal, snapshot) for goal in snapshot.goals],
        active_challenges=[challenge_payload(item, snapshot) for item in snapshot.challenges if item.status in {"accepted", "completed"}],
        challenge_suggestions=[challenge_payload(item, snapshot) for item in snapshot.challenges if item.status == "suggested"],
        ai_challenges_available=ai_challenges_available(get_settings()),
        badges=badge_payloads(snapshot),
        streak=snapshot.streak,
        record_chases=snapshot_record_chases(snapshot),
        discoveries=discovery_summary_payload(snapshot.discoveries),
        annual_awards=annual_award_payloads(snapshot),
    )
    db.commit()
    return response
