package de.avento.app.ui.health

import de.avento.app.MainDispatcherRule
import de.avento.app.data.AventoRepository
import de.avento.app.data.model.Activity
import de.avento.app.data.model.ActivityList
import de.avento.app.data.model.ActivityTrack
import de.avento.app.data.model.HealthConnectionStatus
import de.avento.app.data.model.HealthData
import de.avento.app.data.model.HealthOAuthStart
import de.avento.app.data.model.HealthOverview
import de.avento.app.data.model.HealthSyncResult
import de.avento.app.data.model.OverviewStatistics
import de.avento.app.data.model.Profile
import de.avento.app.data.model.SummaryResponse
import de.avento.app.data.model.WeatherResponse
import de.avento.app.data.security.AuthTokens
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import java.io.IOException
import java.time.Instant
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test

class HealthViewModelTest {
    @get:Rule val mainDispatcher = MainDispatcherRule()

    @Test
    fun `disconnected status does not load private health sections`() {
        val repository = HealthRecordingRepository()

        val viewModel = HealthViewModel(repository)

        assertFalse(viewModel.state.value.initialLoading)
        assertFalse(viewModel.state.value.connected)
        assertEquals(1, repository.connectionCalls)
        assertEquals(0, repository.dataCalls)
        assertEquals(0, repository.scoreCalls)
    }

    @Test
    fun `server scopes drive repair state without Android health permissions`() {
        val repository = HealthRecordingRepository().apply {
            connection = HealthConnectionStatus(
                connected = true,
                status = "connected",
                grantedScopes = listOf("activity_and_fitness.readonly"),
                missingScopes = listOf("sleep.readonly"),
            )
        }

        val viewModel = HealthViewModel(repository)

        assertTrue(viewModel.state.value.connected)
        assertTrue(viewModel.state.value.needsScopeRepair)
        assertEquals(1, repository.dataCalls)
        assertEquals(1, repository.scoreCalls)
    }

    @Test
    fun `one failed section keeps successful data as partial result`() {
        val repository = HealthRecordingRepository().apply {
            connection = HealthConnectionStatus(connected = true, status = "connected")
            scoreFailure = IOException("offline")
        }

        val viewModel = HealthViewModel(repository) { "Keine Verbindung" }

        assertNotNull(viewModel.state.value.data)
        assertNull(viewModel.state.value.overview)
        assertTrue(viewModel.state.value.hasPartialData)
        assertEquals("Keine Verbindung", viewModel.state.value.scoresError)
    }

    @Test
    fun `manual sync reloads backend state and never starts background work`() {
        val repository = HealthRecordingRepository().apply {
            connection = HealthConnectionStatus(connected = true, status = "connected")
        }
        val viewModel = HealthViewModel(repository)

        viewModel.synchronize()

        assertEquals(1, repository.syncCalls)
        assertEquals(2, repository.connectionCalls)
        assertFalse(viewModel.state.value.syncing)
        assertTrue(viewModel.state.value.message?.contains("synchronisiert") == true)
    }

    @Test
    fun `resume refresh can reload status after browser OAuth`() {
        val repository = HealthRecordingRepository()
        val viewModel = HealthViewModel(repository)
        repository.connection = HealthConnectionStatus(connected = true, status = "connected")

        viewModel.refresh()

        assertEquals(2, repository.connectionCalls)
        assertTrue(viewModel.state.value.connected)
    }

    @Test
    fun `first foreground performs one sync when backend data is stale`() {
        val repository = HealthRecordingRepository().apply {
            connection = HealthConnectionStatus(
                connected = true,
                status = "connected",
                lastSyncAt = "2026-07-12T01:00:00Z",
            )
        }
        val viewModel = HealthViewModel(repository)

        viewModel.onForeground(Instant.parse("2026-07-12T12:00:00Z"))
        viewModel.onForeground(Instant.parse("2026-07-12T13:00:00Z"))

        assertEquals(1, repository.syncCalls)
        assertFalse(viewModel.state.value.syncing)
    }

    @Test
    fun `foreground does not sync fresh or incompletely authorized connection`() {
        val freshRepository = HealthRecordingRepository().apply {
            connection = HealthConnectionStatus(
                connected = true,
                status = "connected",
                lastSyncAt = "2026-07-12T10:00:00Z",
            )
        }
        val freshViewModel = HealthViewModel(freshRepository)

        freshViewModel.onForeground(Instant.parse("2026-07-12T12:00:00Z"))

        assertEquals(0, freshRepository.syncCalls)
        assertFalse(
            shouldAutomaticallySyncHealth(
                HealthConnectionStatus(
                    connected = true,
                    status = "connected",
                    missingScopes = listOf("sleep.readonly"),
                ),
                Instant.parse("2026-07-12T12:00:00Z"),
            ),
        )
    }

    @Test
    fun `view model emits only validated OAuth URL`() {
        val repository = HealthRecordingRepository().apply {
            oauthStart = HealthOAuthStart(
                authorizationUrl = "https://accounts.google.com/o/oauth2/v2/auth?state=safe&code_challenge=challenge",
                expiresAt = "2026-07-12T12:00:00Z",
            )
        }
        val viewModel = HealthViewModel(repository)

        viewModel.startOAuth()

        assertNotNull(viewModel.state.value.oauthLaunch)
        assertNull(viewModel.state.value.actionError)
        assertEquals(1, repository.oauthCalls)
    }

    @Test
    fun `reauthorization status forces a fresh Google consent`() {
        val repository = HealthRecordingRepository().apply {
            connection = HealthConnectionStatus(
                connected = false,
                status = "reauthorization_required",
            )
        }
        val viewModel = HealthViewModel(repository)

        viewModel.startOAuth()

        assertTrue(viewModel.state.value.hasConnection)
        assertTrue(repository.lastForceConsent)
        assertNotNull(viewModel.state.value.oauthLaunch)
    }

    @Test
    fun `view model blocks untrusted OAuth URL`() {
        val repository = HealthRecordingRepository().apply {
            oauthStart = HealthOAuthStart(
                authorizationUrl = "https://accounts.google.com.evil.example/o/oauth2/v2/auth",
                expiresAt = "2026-07-12T12:00:00Z",
            )
        }
        val viewModel = HealthViewModel(repository)

        viewModel.startOAuth()

        assertNull(viewModel.state.value.oauthLaunch)
        assertTrue(viewModel.state.value.actionError?.contains("nicht vertrauenswürdig") == true)
    }

    @Test
    fun `Google OAuth URL validation rejects unsafe schemes and lookalikes`() {
        assertTrue(
            isSafeHealthOAuthUrl(
                "https://accounts.google.com/o/oauth2/v2/auth?client_id=id&state=state",
                mockMode = false,
            ),
        )
        assertFalse(isSafeHealthOAuthUrl("http://accounts.google.com/o/oauth2/v2/auth", mockMode = false))
        assertFalse(isSafeHealthOAuthUrl("javascript:alert(1)", mockMode = false))
        assertFalse(
            isSafeHealthOAuthUrl(
                "https://accounts.google.com.evil.example/o/oauth2/v2/auth",
                mockMode = false,
            ),
        )
        assertFalse(
            isSafeHealthOAuthUrl(
                "https://accounts.google.com@evil.example/o/oauth2/v2/auth",
                mockMode = false,
            ),
        )
        assertFalse(
            isSafeHealthOAuthUrl(
                "https://accounts.google.com/o/oauth2/v2/auth#token=secret",
                mockMode = false,
            ),
        )
    }

    @Test
    fun `local OAuth callback is accepted only in explicit mock mode`() {
        val callback = "http://127.0.0.1:8000/api/v1/health/oauth/callback?code=mock-code&state=state"

        assertTrue(isSafeHealthOAuthUrl(callback, mockMode = true))
        assertFalse(isSafeHealthOAuthUrl(callback, mockMode = false))
        assertFalse(
            isSafeHealthOAuthUrl(
                "http://example.com/api/v1/health/oauth/callback?code=mock-code",
                mockMode = true,
            ),
        )
    }

    @Test
    fun `health response models map backend sources and score coverage`() {
        val moshi = Moshi.Builder().addLast(KotlinJsonAdapterFactory()).build()
        val connection = moshi.adapter(HealthConnectionStatus::class.java).fromJson(
            """{
                "provider":"google_health_api_v4",
                "enabled":true,
                "mock_mode":false,
                "connected":true,
                "status":"connected",
                "granted_scopes":["sleep.readonly"],
                "missing_scopes":[],
                "data_sources":[{
                    "platform":"ANDROID",
                    "device_name":"Pixel Watch",
                    "device_manufacturer":"Google",
                    "application_name":"Google Health",
                    "last_seen_at":"2026-07-12T10:00:00Z"
                }]
            }""".trimIndent(),
        )
        val overview = moshi.adapter(HealthOverview::class.java).fromJson(
            """{
                "date":"2026-07-12",
                "generated_at":"2026-07-12T12:00:00Z",
                "scores":{
                    "recovery":{
                        "key":"recovery",
                        "label":"Recovery",
                        "value":78,
                        "data_coverage":{"fraction":0.8,"percent":80.0}
                    }
                }
            }""".trimIndent(),
        )

        assertEquals("Pixel Watch", connection?.sources?.single()?.deviceName)
        assertTrue(connection?.enabled == true)
        assertEquals(78, overview?.scores?.get("recovery")?.value)
        assertEquals(80.0, overview?.scores?.get("recovery")?.dataCoverage?.percent ?: 0.0, 0.0)
    }
}

private class HealthRecordingRepository : AventoRepository {
    override val session: Flow<AuthTokens?> = MutableStateFlow(null)
    var connection = HealthConnectionStatus()
    var data = HealthData()
    var overview = HealthOverview("2026-07-12", "2026-07-12T12:00:00Z")
    var oauthStart = HealthOAuthStart(
        "https://accounts.google.com/o/oauth2/v2/auth?state=state",
        "2026-07-12T12:00:00Z",
    )
    var scoreFailure: Throwable? = null
    var connectionCalls = 0
    var dataCalls = 0
    var scoreCalls = 0
    var oauthCalls = 0
    var syncCalls = 0
    var lastForceConsent = false

    override suspend fun healthConnection(): HealthConnectionStatus {
        connectionCalls++
        return connection
    }

    override suspend fun healthData(dateFrom: String?, dateTo: String?): HealthData {
        dataCalls++
        return data
    }

    override suspend fun healthScores(day: String?): HealthOverview {
        scoreCalls++
        scoreFailure?.let { throw it }
        return overview
    }

    override suspend fun startHealthOAuth(forceConsent: Boolean): HealthOAuthStart {
        oauthCalls++
        lastForceConsent = forceConsent
        return oauthStart
    }

    override suspend fun syncHealth(lookbackDays: Int?): HealthSyncResult {
        syncCalls++
        return HealthSyncResult(
            runId = "run-1",
            status = "succeeded",
            rangeStart = "2026-07-05T00:00:00Z",
            rangeEnd = "2026-07-12T00:00:00Z",
        )
    }

    override suspend fun currentSession(): AuthTokens? = null
    override suspend fun login(email: String, password: String) = Unit
    override suspend fun register(email: String, password: String, displayName: String, inviteToken: String) = Unit
    override suspend fun bootstrap(email: String, password: String, displayName: String, bootstrapCode: String) = Unit
    override suspend fun resetPassword(token: String, newPassword: String) = Unit
    override suspend fun changePassword(currentPassword: String, newPassword: String) = Unit
    override suspend fun logout() = Unit
    override suspend fun profile() = Profile("1", "radler@example.de", "Radler")
    override suspend fun activities(query: String?) = ActivityList()
    override suspend fun statistics() = OverviewStatistics()
    override suspend fun uploadTcx(
        bytes: ByteArray,
        fileName: String,
        title: String?,
        type: String?,
        notes: String?,
    ) = Activity("1")
    override suspend fun activity(id: String) = Activity(id)
    override suspend fun track(id: String) = ActivityTrack(id)
    override suspend fun weather(id: String) = WeatherResponse("pending")
    override suspend fun refreshWeather(id: String) = WeatherResponse("pending")
    override suspend fun summary(id: String) = SummaryResponse("")
    override suspend fun generateSummary(id: String, force: Boolean) = SummaryResponse("")
    override suspend fun updateActivity(id: String, title: String?, type: String?, notes: String?) = Activity(id)
    override suspend fun deleteActivity(id: String) = Unit
}
