package de.avento.app.data

import de.avento.app.data.model.Activity
import de.avento.app.data.model.ActivityList
import de.avento.app.data.model.ActivityTrack
import de.avento.app.data.model.ActivityUpdate
import de.avento.app.data.model.BootstrapRequest
import de.avento.app.data.model.LoginRequest
import de.avento.app.data.model.OverviewStatistics
import de.avento.app.data.model.PasswordChangeRequest
import de.avento.app.data.model.PasswordResetRequest
import de.avento.app.data.model.Profile
import de.avento.app.data.model.RegisterRequest
import de.avento.app.data.model.SummaryResponse
import de.avento.app.data.model.WeatherResponse
import de.avento.app.data.model.RefreshRequest
import de.avento.app.data.network.AventoApi
import de.avento.app.data.security.AuthTokens
import de.avento.app.data.security.TokenStore
import kotlinx.coroutines.flow.Flow
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import retrofit2.HttpException

interface AventoRepository {
    val session: Flow<AuthTokens?>
    suspend fun currentSession(): AuthTokens?
    suspend fun login(email: String, password: String)
    suspend fun register(email: String, password: String, displayName: String, inviteToken: String)
    suspend fun bootstrap(email: String, password: String, displayName: String, bootstrapCode: String)
    suspend fun resetPassword(token: String, newPassword: String)
    suspend fun changePassword(currentPassword: String, newPassword: String)
    suspend fun logout()
    suspend fun profile(): Profile
    suspend fun activities(query: String? = null): ActivityList
    suspend fun statistics(): OverviewStatistics
    suspend fun uploadTcx(bytes: ByteArray, fileName: String, title: String?, type: String?, notes: String?): Activity
    suspend fun activity(id: String): Activity
    suspend fun track(id: String): ActivityTrack
    suspend fun weather(id: String): WeatherResponse
    suspend fun refreshWeather(id: String): WeatherResponse
    suspend fun summary(id: String): SummaryResponse
    suspend fun generateSummary(id: String, force: Boolean = false): SummaryResponse
    suspend fun updateActivity(id: String, title: String?, type: String?, notes: String?): Activity
    suspend fun deleteActivity(id: String)
}

class DefaultAventoRepository(
    private val publicApi: AventoApi,
    private val api: AventoApi,
    private val tokenStore: TokenStore,
) : AventoRepository {
    override val session: Flow<AuthTokens?> = tokenStore.tokens

    override suspend fun currentSession(): AuthTokens? = tokenStore.read()

    override suspend fun login(email: String, password: String) {
        publicApi.login(LoginRequest(email.trim(), password)).save()
    }

    override suspend fun register(
        email: String,
        password: String,
        displayName: String,
        inviteToken: String,
    ) {
        publicApi.register(RegisterRequest(email.trim(), password, displayName.trim(), inviteToken.trim())).save()
    }

    override suspend fun bootstrap(email: String, password: String, displayName: String, bootstrapCode: String) {
        publicApi.bootstrap(BootstrapRequest(email.trim(), password, displayName.trim(), bootstrapCode.trim())).save()
    }

    override suspend fun resetPassword(token: String, newPassword: String) {
        val response = publicApi.resetPassword(PasswordResetRequest(token.trim(), newPassword))
        if (!response.isSuccessful) throw HttpException(response)
    }

    override suspend fun changePassword(currentPassword: String, newPassword: String) {
        val response = api.changePassword(PasswordChangeRequest(currentPassword, newPassword))
        if (!response.isSuccessful) throw HttpException(response)
    }

    override suspend fun logout() {
        val refreshToken = tokenStore.read()?.refreshToken
        try {
            if (refreshToken != null) api.logout(RefreshRequest(refreshToken))
        } finally {
            tokenStore.clear()
        }
    }

    override suspend fun profile(): Profile = api.profile()

    override suspend fun activities(query: String?): ActivityList =
        api.activities(query = query?.trim()?.takeIf(String::isNotEmpty))

    override suspend fun statistics(): OverviewStatistics = api.statistics()

    override suspend fun uploadTcx(
        bytes: ByteArray,
        fileName: String,
        title: String?,
        type: String?,
        notes: String?,
    ): Activity {
        require(bytes.isNotEmpty()) { "Die TCX-Datei ist leer." }
        val xml = "application/vnd.garmin.tcx+xml".toMediaType()
        val text = "text/plain".toMediaType()
        val file = MultipartBody.Part.createFormData("file", fileName, bytes.toRequestBody(xml))
        return api.uploadActivity(
            file = file,
            title = title.partOrNull(text),
            type = type.partOrNull(text),
            notes = notes.partOrNull(text),
        )
    }

    override suspend fun activity(id: String): Activity = api.activity(id)
    override suspend fun track(id: String): ActivityTrack = api.track(id)
    override suspend fun weather(id: String): WeatherResponse = api.weather(id)
    override suspend fun refreshWeather(id: String): WeatherResponse = api.refreshWeather(id)
    override suspend fun summary(id: String): SummaryResponse = api.summary(id)
    override suspend fun generateSummary(id: String, force: Boolean): SummaryResponse =
        api.generateSummary(id, force)

    override suspend fun updateActivity(
        id: String,
        title: String?,
        type: String?,
        notes: String?,
    ): Activity = api.updateActivity(id, ActivityUpdate(title, type, notes))

    override suspend fun deleteActivity(id: String) {
        val response = api.deleteActivity(id)
        if (!response.isSuccessful) error("Aktivität konnte nicht gelöscht werden (${response.code()}).")
    }

    private suspend fun de.avento.app.data.model.TokenResponse.save() {
        tokenStore.save(accessToken, refreshToken)
    }

    private fun String?.partOrNull(mediaType: okhttp3.MediaType) =
        this?.trim()?.takeIf(String::isNotEmpty)?.toRequestBody(mediaType)
}
