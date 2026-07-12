from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import date, datetime, timedelta, timezone
from collections import defaultdict
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from ..config import Settings, get_settings
from ..database import get_db
from ..deps import get_current_user
from ..google_health_client import (
    GOOGLE_HEALTH_SCOPES,
    GoogleHealthError,
    get_google_health_client,
)
from ..health_models import (
    HealthConnection,
    HealthDataSource,
    HealthExercise,
    HealthHeartRateAggregate,
    HealthMetric,
    HealthOAuthState,
    HealthSleepSession,
    HealthSyncRun,
)
from ..health_scores import DailyHealthData, calculate_health_scores
from ..health_schemas import (
    HealthConnectionStatus,
    HealthDataResponse,
    HealthExerciseResponse,
    HealthHeartRateResponse,
    HealthMetricResponse,
    HealthOAuthStartResponse,
    HealthOverviewResponse,
    HealthSleepResponse,
    HealthSyncRequest,
    HealthSyncResponse,
)
from ..health_sync import synchronize_health_data
from ..models import User
from ..security import (
    decrypt_health_secret,
    encrypt_health_secret,
    token_hash,
)


router = APIRouter(prefix="/health", tags=["Google Health"])


@router.post("/oauth/start", response_model=HealthOAuthStartResponse)
def start_google_health_oauth(
    force_consent: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HealthOAuthStartResponse:
    settings = get_settings()
    _require_health_configuration(settings)
    redirect_uri = settings.google_health_redirect_uri or ""
    _validate_redirect_uri(redirect_uri, settings)
    state_value = secrets.token_urlsafe(48)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    db.add(
        HealthOAuthState(
            user_id=current_user.id,
            state_hash=token_hash(state_value),
            pkce_verifier_encrypted=encrypt_health_secret(verifier),
            redirect_uri=redirect_uri,
            requested_scopes=list(GOOGLE_HEALTH_SCOPES),
            expires_at=expires_at,
        )
    )
    db.commit()
    client = get_google_health_client(settings)
    try:
        authorization_url = client.authorization_url(
            state=state_value,
            code_challenge=challenge,
            force_consent=force_consent,
        )
    except GoogleHealthError as exc:
        raise HTTPException(status_code=exc.status_code, detail="Google Health ist nicht konfiguriert.") from None
    return HealthOAuthStartResponse(
        authorization_url=authorization_url,
        expires_at=expires_at,
        mock_mode=settings.google_health_mock_mode,
    )


@router.get("/oauth/callback", response_model=None)
def google_health_oauth_callback(
    state_value: str = Query(alias="state", min_length=20, max_length=512),
    code: str | None = Query(default=None, max_length=4096),
    error: str | None = Query(default=None, max_length=200),
    db: Session = Depends(get_db),
) -> RedirectResponse | dict[str, str]:
    settings = get_settings()
    _require_health_configuration(settings)
    stored = db.scalar(
        select(HealthOAuthState)
        .where(HealthOAuthState.state_hash == token_hash(state_value))
        .with_for_update()
    )
    now = datetime.now(timezone.utc)
    if (
        stored is None
        or stored.consumed_at is not None
        or _aware(stored.expires_at) <= now
        or stored.redirect_uri != settings.google_health_redirect_uri
        or list(stored.requested_scopes or []) != list(GOOGLE_HEALTH_SCOPES)
    ):
        raise HTTPException(status_code=400, detail="Ungültiger oder abgelaufener OAuth-Vorgang.")
    stored.consumed_at = now
    db.commit()
    if error or not code:
        return _callback_result(settings, "denied")
    verifier = decrypt_health_secret(stored.pkce_verifier_encrypted)
    if not verifier:
        raise HTTPException(status_code=400, detail="Ungültiger OAuth-Vorgang.")
    client = get_google_health_client(settings)
    try:
        token = client.exchange_code(code=code, code_verifier=verifier, redirect_uri=stored.redirect_uri)
        granted = list(token.get("scope") or [])
        if not set(GOOGLE_HEALTH_SCOPES).issubset(set(granted)):
            raise GoogleHealthError("missing_google_health_scopes", status_code=403)
        identity = client.get_identity(token["access_token"])
    except GoogleHealthError as exc:
        raise HTTPException(
            status_code=400 if exc.status_code < 500 else 502,
            detail="Die Google-Health-Verbindung konnte nicht abgeschlossen werden.",
        ) from None
    external_id = identity["health_user_id"]
    external_hash = token_hash(external_id)
    connection = db.scalar(select(HealthConnection).where(HealthConnection.user_id == stored.user_id))
    if connection is None:
        connection = HealthConnection(
            user_id=stored.user_id,
            health_user_id_hash=external_hash,
            health_user_id_encrypted=encrypt_health_secret(external_id),
            access_token_encrypted=encrypt_health_secret(token["access_token"]),
            access_token_expires_at=now + timedelta(seconds=int(token["expires_in"])),
        )
        db.add(connection)
    connection.health_user_id_hash = external_hash
    connection.health_user_id_encrypted = encrypt_health_secret(external_id)
    connection.access_token_encrypted = encrypt_health_secret(token["access_token"])
    if token.get("refresh_token"):
        connection.refresh_token_encrypted = encrypt_health_secret(token["refresh_token"])
    if not connection.refresh_token_encrypted:
        raise HTTPException(status_code=400, detail="Google hat keinen erneuerbaren Zugriff gewährt.")
    connection.access_token_expires_at = now + timedelta(seconds=int(token["expires_in"]))
    refresh_expires = token.get("refresh_token_expires_in")
    connection.refresh_token_expires_at = (
        now + timedelta(seconds=int(refresh_expires)) if refresh_expires is not None else None
    )
    connection.granted_scopes = granted
    connection.status = "connected"
    connection.last_error_code = None
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Dieses Google-Health-Konto ist bereits mit einem anderen Avento-Konto verbunden.",
        ) from None
    return _callback_result(settings, "connected")


@router.get("/status", response_model=HealthConnectionStatus)
def google_health_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HealthConnectionStatus:
    settings = get_settings()
    connection = db.scalar(select(HealthConnection).where(HealthConnection.user_id == current_user.id))
    if connection is None:
        return HealthConnectionStatus(
            enabled=settings.google_health_enabled or settings.google_health_mock_mode,
            mock_mode=settings.google_health_mock_mode,
            connected=False,
            status="disconnected",
            missing_scopes=list(GOOGLE_HEALTH_SCOPES),
        )
    granted = list(connection.granted_scopes or [])
    return HealthConnectionStatus(
        enabled=settings.google_health_enabled or settings.google_health_mock_mode,
        mock_mode=settings.google_health_mock_mode,
        connected=connection.status == "connected",
        status=connection.status,
        granted_scopes=granted,
        missing_scopes=[scope for scope in GOOGLE_HEALTH_SCOPES if scope not in granted],
        last_sync_at=connection.last_sync_at,
        last_error_code=connection.last_error_code,
        data_sources=db.scalars(
            select(HealthDataSource)
            .where(HealthDataSource.connection_id == connection.id)
            .order_by(HealthDataSource.last_seen_at.desc())
        ).all(),
    )


@router.post("/sync", response_model=HealthSyncResponse)
def sync_google_health(
    payload: HealthSyncRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HealthSyncResponse:
    settings = get_settings()
    connection = db.scalar(select(HealthConnection).where(HealthConnection.user_id == current_user.id))
    if connection is None:
        raise HTTPException(status_code=409, detail="Google Health ist nicht verbunden.")
    if connection.last_sync_at is not None and settings.google_health_min_sync_interval_seconds:
        elapsed = (datetime.now(timezone.utc) - _aware(connection.last_sync_at)).total_seconds()
        remaining = settings.google_health_min_sync_interval_seconds - elapsed
        if remaining > 0:
            raise HTTPException(
                status_code=429,
                detail="Bitte warte kurz vor der nächsten Synchronisation.",
                headers={"Retry-After": str(max(1, int(remaining + 0.999)))},
            )
    active = db.scalar(
        select(HealthSyncRun).where(
            HealthSyncRun.user_id == current_user.id,
            HealthSyncRun.status == "running",
        )
    )
    if active is not None:
        raise HTTPException(status_code=409, detail="Eine Synchronisation läuft bereits.")
    run = synchronize_health_data(
        db,
        connection=connection,
        client=get_google_health_client(),
        lookback_days=payload.lookback_days,
    )
    return HealthSyncResponse(
        run_id=run.id,
        status=run.status,
        range_start=run.range_start,
        range_end=run.range_end,
        fetched_count=run.fetched_count,
        stored_count=run.stored_count,
        rejected_count=run.rejected_count,
        error_code=run.error_code,
    )


@router.get("/data", response_model=HealthDataResponse)
def get_health_data(
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=1000, ge=1, le=5000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HealthDataResponse:
    if date_from and date_to and date_to < date_from:
        raise HTTPException(status_code=422, detail="date_to muss nach date_from liegen.")
    metric_query = select(HealthMetric).where(HealthMetric.user_id == current_user.id)
    hr_query = select(HealthHeartRateAggregate).where(HealthHeartRateAggregate.user_id == current_user.id)
    sleep_query = (
        select(HealthSleepSession)
        .options(selectinload(HealthSleepSession.stages))
        .where(HealthSleepSession.user_id == current_user.id)
    )
    exercise_query = select(HealthExercise).where(HealthExercise.user_id == current_user.id)
    if date_from:
        metric_query = metric_query.where(HealthMetric.local_date >= date_from)
        hr_query = hr_query.where(HealthHeartRateAggregate.local_date >= date_from)
        sleep_query = sleep_query.where(HealthSleepSession.local_date >= date_from)
        exercise_query = exercise_query.where(HealthExercise.local_date >= date_from)
    if date_to:
        metric_query = metric_query.where(HealthMetric.local_date <= date_to)
        hr_query = hr_query.where(HealthHeartRateAggregate.local_date <= date_to)
        sleep_query = sleep_query.where(HealthSleepSession.local_date <= date_to)
        exercise_query = exercise_query.where(HealthExercise.local_date <= date_to)
    metrics = db.scalars(metric_query.order_by(HealthMetric.local_date.desc()).limit(limit)).all()
    heart_rate = db.scalars(hr_query.order_by(HealthHeartRateAggregate.start_at.desc()).limit(limit)).all()
    sleeps = db.scalars(sleep_query.order_by(HealthSleepSession.end_at.desc()).limit(limit)).all()
    exercises = db.scalars(exercise_query.order_by(HealthExercise.start_at.desc()).limit(limit)).all()
    return HealthDataResponse(
        metrics=[HealthMetricResponse.model_validate(item) for item in metrics],
        heart_rate=[HealthHeartRateResponse.model_validate(item) for item in heart_rate],
        sleeps=[HealthSleepResponse.model_validate(item) for item in sleeps],
        exercises=[HealthExerciseResponse.model_validate(item) for item in exercises],
    )


@router.get("/overview", response_model=HealthOverviewResponse)
def get_health_overview(
    day: date | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HealthOverviewResponse:
    target = day or datetime.now(timezone.utc).date()
    start = target - timedelta(days=30)
    metrics = db.scalars(
        select(HealthMetric).where(
            HealthMetric.user_id == current_user.id,
            HealthMetric.local_date >= start,
            HealthMetric.local_date <= target,
        )
    ).all()
    sleeps = db.scalars(
        select(HealthSleepSession).where(
            HealthSleepSession.user_id == current_user.id,
            HealthSleepSession.local_date >= start,
            HealthSleepSession.local_date <= target,
        )
    ).all()
    exercises = db.scalars(
        select(HealthExercise).where(
            HealthExercise.user_id == current_user.id,
            HealthExercise.local_date >= start,
            HealthExercise.local_date <= target,
        )
    ).all()
    rows = _daily_score_rows(start, target, metrics, sleeps, exercises)
    current = next(item for item in rows if item.date == target)
    calculated = calculate_health_scores(current, [item for item in rows if item.date < target])
    score_keys = ("recovery", "energy", "training_load", "resilience")
    scores = {key: calculated[key] for key in score_keys}
    coverage = {
        key: float(scores[key].get("data_coverage", {}).get("fraction", 0.0))
        for key in score_keys
    }
    factors = [
        {"score": key, **factor}
        for key in score_keys
        for factor in scores[key].get("important_factors", [])
    ]
    baselines = {
        key: scores[key].get("metadata", {}).get("baselines", {})
        for key in score_keys
    }
    uncertainty = [
        f"{scores[key].get('label', key)}: {scores[key].get('status', 'unbekannt')}"
        for key in score_keys
        if scores[key].get("value") is None
    ]
    return HealthOverviewResponse(
        date=target,
        generated_at=datetime.now(timezone.utc),
        scores=scores,
        factors=factors,
        coverage=coverage,
        baselines=baselines,
        uncertainty=uncertainty,
    )


@router.delete("/connection", status_code=status.HTTP_204_NO_CONTENT)
def delete_google_health_connection(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    connection = db.scalar(select(HealthConnection).where(HealthConnection.user_id == current_user.id))
    if connection is not None:
        token = decrypt_health_secret(connection.refresh_token_encrypted) or decrypt_health_secret(
            connection.access_token_encrypted
        )
        if token:
            get_google_health_client().revoke_token(token)
        db.delete(connection)
    db.execute(delete(HealthOAuthState).where(HealthOAuthState.user_id == current_user.id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _require_health_configuration(settings: Settings) -> None:
    if not settings.google_health_enabled and not settings.google_health_mock_mode:
        raise HTTPException(status_code=503, detail="Google Health ist deaktiviert.")
    if settings.environment.lower() == "production" and settings.google_health_mock_mode:
        raise HTTPException(status_code=503, detail="Der Google-Health-Mockmodus ist in Produktion unzulässig.")
    if not settings.google_health_token_encryption_key:
        raise HTTPException(status_code=503, detail="Die Google-Health-Tokenverschlüsselung fehlt.")


def _validate_redirect_uri(value: str, settings: Settings) -> None:
    try:
        parsed = urlsplit(value)
    except ValueError:
        parsed = None
    if (
        parsed is None
        or not parsed.hostname
        or parsed.fragment
        or parsed.username
        or parsed.password
        or parsed.scheme not in {"http", "https"}
    ):
        raise HTTPException(status_code=503, detail="Die Google-Health-Redirect-URI ist ungültig.")
    local = parsed.hostname.lower().rstrip(".") in {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme != "https" and not local:
        raise HTTPException(status_code=503, detail="Die Google-Health-Redirect-URI muss HTTPS verwenden.")
    if settings.environment.lower() == "production" and parsed.scheme != "https":
        raise HTTPException(status_code=503, detail="In Produktion ist eine HTTPS-Redirect-URI erforderlich.")


def _callback_result(settings: Settings, result: str) -> RedirectResponse | dict[str, str]:
    target = settings.google_health_success_redirect_uri
    if not target:
        return {"detail": result}
    _validate_redirect_uri(target, settings)
    parsed = urlsplit(target)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["google-health"] = result
    return RedirectResponse(
        url=urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), "")),
        status_code=status.HTTP_303_SEE_OTHER,
    )


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _daily_score_rows(
    start: date,
    end: date,
    metrics: list[HealthMetric],
    sleeps: list[HealthSleepSession],
    exercises: list[HealthExercise],
) -> list[DailyHealthData]:
    metric_days: dict[date, dict[str, float]] = defaultdict(dict)
    for metric in metrics:
        if metric.local_date and metric.metric_type in {"resting_heart_rate", "hrv_rmssd", "steps"}:
            metric_days[metric.local_date][metric.metric_type] = metric.value
    sleep_days: dict[date, HealthSleepSession] = {}
    for sleep in sleeps:
        if sleep.is_nap:
            continue
        duration = sleep.minutes_asleep or (_aware(sleep.end_at) - _aware(sleep.start_at)).total_seconds() / 60
        existing = sleep_days.get(sleep.local_date)
        existing_duration = (
            (existing.minutes_asleep or (_aware(existing.end_at) - _aware(existing.start_at)).total_seconds() / 60)
            if existing
            else -1
        )
        if duration > existing_duration:
            sleep_days[sleep.local_date] = sleep
    zone_days: dict[date, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    active_days: dict[date, float] = defaultdict(float)
    zone_aliases = {
        "lightTime": "light",
        "moderateTime": "moderate",
        "vigorousTime": "vigorous",
        "peakTime": "peak",
    }
    for exercise in exercises:
        if exercise.heart_rate_zone_seconds:
            for source_key, seconds in exercise.heart_rate_zone_seconds.items():
                if source_key in zone_aliases:
                    zone_days[exercise.local_date][zone_aliases[source_key]] += float(seconds) / 60
        if exercise.active_duration_seconds is not None:
            active_days[exercise.local_date] += exercise.active_duration_seconds / 60
    rows: list[DailyHealthData] = []
    current = start
    while current <= end:
        values = metric_days.get(current, {})
        sleep = sleep_days.get(current)
        asleep = float(sleep.minutes_asleep) if sleep and sleep.minutes_asleep is not None else None
        if sleep and asleep is None:
            asleep = (_aware(sleep.end_at) - _aware(sleep.start_at)).total_seconds() / 60
        awake = float(sleep.minutes_awake or 0) if sleep else None
        efficiency = (
            asleep / (asleep + awake) * 100
            if asleep is not None and awake is not None and asleep + awake > 0
            else None
        )
        zones = dict(zone_days[current]) if current in zone_days else None
        rows.append(
            DailyHealthData(
                date=current,
                sleep_minutes=asleep,
                sleep_efficiency_percent=efficiency,
                hrv_rmssd_ms=values.get("hrv_rmssd"),
                resting_heart_rate_bpm=values.get("resting_heart_rate"),
                heart_rate_zone_minutes=zones,
                active_minutes=active_days.get(current) or None,
                steps=int(values["steps"]) if "steps" in values else None,
                # A Health-API day is scoreable as soon as its required
                # morning/sleep signals are present. Missing signals are
                # represented explicitly and already suppress the score.
                is_complete=True,
            )
        )
        current += timedelta(days=1)
    return rows
