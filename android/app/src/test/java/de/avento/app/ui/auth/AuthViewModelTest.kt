package de.avento.app.ui.auth

import de.avento.app.MainDispatcherRule
import de.avento.app.data.AventoRepository
import de.avento.app.data.model.Activity
import de.avento.app.data.model.ActivityList
import de.avento.app.data.model.ActivityTrack
import de.avento.app.data.model.OverviewStatistics
import de.avento.app.data.model.Profile
import de.avento.app.data.model.SummaryResponse
import de.avento.app.data.model.WeatherResponse
import de.avento.app.data.security.AuthTokens
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test

class AuthViewModelTest {
    @get:Rule val mainDispatcher = MainDispatcherRule()

    @Test fun `successful login trims email and completes navigation`() {
        val repository = RecordingRepository()
        val viewModel = AuthViewModel(repository)
        var navigated = false

        viewModel.login("  radler@example.de ", "geheim1234") { navigated = true }

        assertEquals("radler@example.de", repository.email)
        assertTrue(navigated)
        assertFalse(viewModel.state.value.loading)
    }

    @Test fun `invalid email is shown without network call`() {
        val repository = RecordingRepository()
        val viewModel = AuthViewModel(repository)

        viewModel.login("keine-mail", "geheim1234") {}

        assertFalse(repository.loginCalled)
        assertTrue(viewModel.state.value.error?.contains("gültige E-Mail") == true)
    }

    @Test fun `password reset validates and submits trimmed token`() {
        val repository = RecordingRepository()
        val viewModel = AuthViewModel(repository)
        var completed = false

        viewModel.resetPassword("  reset-token-123  ", "neuesPasswort1", "neuesPasswort1") {
            completed = true
        }

        assertTrue(repository.resetCalled)
        assertEquals("reset-token-123", repository.resetToken)
        assertEquals("neuesPasswort1", repository.resetNewPassword)
        assertTrue(completed)
        assertFalse(viewModel.state.value.loading)
    }

    @Test fun `password reset rejects mismatching confirmation`() {
        val repository = RecordingRepository()
        val viewModel = AuthViewModel(repository)

        viewModel.resetPassword("reset-token-123", "neuesPasswort1", "anderesPasswort1") {}

        assertFalse(repository.resetCalled)
        assertTrue(viewModel.state.value.error?.contains("stimmen nicht überein") == true)
    }
}

private class RecordingRepository : AventoRepository {
    override val session: Flow<AuthTokens?> = MutableStateFlow(null)
    var email: String? = null
    var loginCalled = false
    var resetCalled = false
    var resetToken: String? = null
    var resetNewPassword: String? = null

    override suspend fun currentSession(): AuthTokens? = null
    override suspend fun login(email: String, password: String) { loginCalled = true; this.email = email }
    override suspend fun register(email: String, password: String, displayName: String, inviteToken: String) = Unit
    override suspend fun bootstrap(email: String, password: String, displayName: String, bootstrapCode: String) = Unit
    override suspend fun resetPassword(token: String, newPassword: String) {
        resetCalled = true
        resetToken = token
        resetNewPassword = newPassword
    }
    override suspend fun changePassword(currentPassword: String, newPassword: String) = Unit
    override suspend fun logout() = Unit
    override suspend fun profile() = Profile("1", "radler@example.de", "Radler")
    override suspend fun activities(query: String?) = ActivityList()
    override suspend fun statistics() = OverviewStatistics()
    override suspend fun uploadTcx(bytes: ByteArray, fileName: String, title: String?, type: String?, notes: String?) = Activity("1")
    override suspend fun activity(id: String) = Activity(id)
    override suspend fun track(id: String) = ActivityTrack(id)
    override suspend fun weather(id: String) = WeatherResponse("pending")
    override suspend fun refreshWeather(id: String) = WeatherResponse("pending")
    override suspend fun summary(id: String) = SummaryResponse("")
    override suspend fun generateSummary(id: String, force: Boolean) = SummaryResponse("")
    override suspend fun updateActivity(id: String, title: String?, type: String?, notes: String?) = Activity(id)
    override suspend fun deleteActivity(id: String) = Unit
}
