package de.avento.app.data.model

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = false)
data class LoginRequest(val email: String, val password: String)

@JsonClass(generateAdapter = false)
data class RegisterRequest(
    val email: String,
    val password: String,
    @param:Json(name = "display_name") val displayName: String,
    @param:Json(name = "invite_token") val inviteToken: String,
)

@JsonClass(generateAdapter = false)
data class BootstrapRequest(
    val email: String,
    val password: String,
    @param:Json(name = "display_name") val displayName: String,
    @param:Json(name = "bootstrap_code") val bootstrapCode: String,
)

@JsonClass(generateAdapter = false)
data class RefreshRequest(@param:Json(name = "refresh_token") val refreshToken: String)

@JsonClass(generateAdapter = false)
data class PasswordResetRequest(
    val token: String,
    @param:Json(name = "new_password") val newPassword: String,
)

@JsonClass(generateAdapter = false)
data class PasswordChangeRequest(
    @param:Json(name = "current_password") val currentPassword: String,
    @param:Json(name = "new_password") val newPassword: String,
)

@JsonClass(generateAdapter = false)
data class TokenResponse(
    @param:Json(name = "access_token") val accessToken: String,
    @param:Json(name = "refresh_token") val refreshToken: String,
    @param:Json(name = "token_type") val tokenType: String = "bearer",
    @param:Json(name = "expires_in") val expiresIn: Long = 0,
)

@JsonClass(generateAdapter = false)
data class HeartRateZone(
    val name: String,
    @param:Json(name = "min_bpm") val minBpm: Int,
    @param:Json(name = "max_bpm") val maxBpm: Int,
    val color: String,
)

@JsonClass(generateAdapter = false)
data class Profile(
    val id: String,
    val email: String,
    @param:Json(name = "display_name") val displayName: String,
    @param:Json(name = "hr_max") val heartRateMax: Int? = null,
    @param:Json(name = "hr_rest") val heartRateRest: Int? = null,
    @param:Json(name = "hr_zones") val heartRateZones: List<HeartRateZone> = emptyList(),
    @param:Json(name = "training_goals") val trainingGoals: List<String> = emptyList(),
    @param:Json(name = "avatar_data_url") val avatarDataUrl: String? = null,
)

@JsonClass(generateAdapter = false)
data class ProfileUpdate(
    @param:Json(name = "display_name") val displayName: String? = null,
    @param:Json(name = "hr_max") val heartRateMax: Int? = null,
    @param:Json(name = "hr_rest") val heartRateRest: Int? = null,
)

@JsonClass(generateAdapter = false)
data class Activity(
    val id: String,
    val title: String? = null,
    val type: String? = null,
    val notes: String? = null,
    @param:Json(name = "original_filename") val originalFilename: String? = null,
    @param:Json(name = "started_at") val startedAt: String? = null,
    @param:Json(name = "ended_at") val endedAt: String? = null,
    @param:Json(name = "distance_m") val distanceMeters: Double? = null,
    @param:Json(name = "duration_s") val durationSeconds: Double? = null,
    @param:Json(name = "moving_time_s") val movingTimeSeconds: Double? = null,
    @param:Json(name = "pause_time_s") val pauseTimeSeconds: Double? = null,
    @param:Json(name = "avg_speed_mps") val averageSpeedMps: Double? = null,
    @param:Json(name = "max_speed_mps") val maxSpeedMps: Double? = null,
    @param:Json(name = "elevation_gain_m") val elevationGainMeters: Double? = null,
    @param:Json(name = "avg_hr_bpm") val averageHeartRate: Double? = null,
    @param:Json(name = "max_hr_bpm") val maxHeartRate: Double? = null,
    @param:Json(name = "avg_cadence_rpm") val averageCadence: Double? = null,
    @param:Json(name = "max_cadence_rpm") val maxCadence: Double? = null,
    @param:Json(name = "avg_power_w") val averagePower: Double? = null,
    @param:Json(name = "max_power_w") val maxPower: Double? = null,
    @param:Json(name = "training_load") val trainingLoad: Double? = null,
    @param:Json(name = "hr_zone_seconds") val heartRateZoneSeconds: Map<String, Double> = emptyMap(),
    val weather: Map<String, Any?>? = null,
    @param:Json(name = "weather_status") val weatherStatus: String? = null,
    @param:Json(name = "ai_summary") val aiSummary: String? = null,
    @param:Json(name = "ai_provider") val aiProvider: String? = null,
    @param:Json(name = "created_at") val createdAt: String? = null,
    @param:Json(name = "updated_at") val updatedAt: String? = null,
)

@JsonClass(generateAdapter = false)
data class ActivityList(
    val items: List<Activity> = emptyList(),
    val total: Int = 0,
    val limit: Int = 50,
    val offset: Int = 0,
)

@JsonClass(generateAdapter = false)
data class ActivityUpdate(
    val title: String? = null,
    val type: String? = null,
    val notes: String? = null,
)

@JsonClass(generateAdapter = false)
data class TrackPoint(
    val time: String? = null,
    val latitude: Double? = null,
    val longitude: Double? = null,
    @param:Json(name = "altitude_m") val altitudeMeters: Double? = null,
    @param:Json(name = "distance_m") val distanceMeters: Double? = null,
    @param:Json(name = "heart_rate_bpm") val heartRate: Double? = null,
    @param:Json(name = "cadence_rpm") val cadence: Double? = null,
    @param:Json(name = "power_w") val power: Double? = null,
    @param:Json(name = "speed_mps") val speedMps: Double? = null,
)

@JsonClass(generateAdapter = false)
data class ActivityTrack(
    @param:Json(name = "activity_id") val activityId: String,
    val points: List<TrackPoint> = emptyList(),
)

@JsonClass(generateAdapter = false)
data class WeatherResponse(
    val status: String,
    val data: Map<String, Any?>? = null,
    @param:Json(name = "updated_at") val updatedAt: String? = null,
)

@JsonClass(generateAdapter = false)
data class SummaryResponse(
    val summary: String,
    val provider: String? = null,
    @param:Json(name = "updated_at") val updatedAt: String? = null,
)

@JsonClass(generateAdapter = false)
data class MonthStatistics(
    val month: String,
    @param:Json(name = "activity_count") val activityCount: Int = 0,
    @param:Json(name = "distance_m") val distanceMeters: Double = 0.0,
    @param:Json(name = "duration_s") val durationSeconds: Double = 0.0,
    @param:Json(name = "elevation_gain_m") val elevationGainMeters: Double = 0.0,
    @param:Json(name = "training_load") val trainingLoad: Double = 0.0,
)

@JsonClass(generateAdapter = false)
data class OverviewStatistics(
    @param:Json(name = "activity_count") val activityCount: Int = 0,
    @param:Json(name = "distance_m") val distanceMeters: Double = 0.0,
    @param:Json(name = "duration_s") val durationSeconds: Double = 0.0,
    @param:Json(name = "moving_time_s") val movingTimeSeconds: Double = 0.0,
    @param:Json(name = "elevation_gain_m") val elevationGainMeters: Double = 0.0,
    @param:Json(name = "training_load") val trainingLoad: Double = 0.0,
    @param:Json(name = "avg_speed_mps") val averageSpeedMps: Double? = null,
    @param:Json(name = "by_month") val byMonth: List<MonthStatistics> = emptyList(),
)

@JsonClass(generateAdapter = false)
data class CompareRequest(@param:Json(name = "activity_ids") val activityIds: List<String>)

@JsonClass(generateAdapter = false)
data class CompareResponse(val activities: List<Activity>)

@JsonClass(generateAdapter = false)
data class ApiError(val detail: String? = null)
