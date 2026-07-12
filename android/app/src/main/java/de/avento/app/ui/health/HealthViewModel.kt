package de.avento.app.ui.health

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import de.avento.app.data.AventoRepository
import de.avento.app.data.model.HealthConnectionStatus
import de.avento.app.data.model.HealthData
import de.avento.app.data.model.HealthOverview
import java.time.Duration
import java.time.Instant
import java.time.OffsetDateTime
import java.net.URI
import java.util.Locale
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class HealthOAuthLaunch(
    val authorizationUrl: String,
    val mockMode: Boolean,
)

data class HealthUiState(
    val initialLoading: Boolean = true,
    val refreshing: Boolean = false,
    val connecting: Boolean = false,
    val syncing: Boolean = false,
    val disconnecting: Boolean = false,
    val connection: HealthConnectionStatus? = null,
    val data: HealthData? = null,
    val overview: HealthOverview? = null,
    val connectionError: String? = null,
    val dataError: String? = null,
    val scoresError: String? = null,
    val actionError: String? = null,
    val message: String? = null,
    val oauthLaunch: HealthOAuthLaunch? = null,
) {
    val connected: Boolean
        get() = connection?.connected == true

    val hasConnection: Boolean
        get() = connected || connection?.status !in setOf(null, "", "disconnected")

    val needsScopeRepair: Boolean
        get() = connected && connection?.missingScopes?.isNotEmpty() == true

    val hasPartialData: Boolean
        get() = connected && (dataError != null || scoresError != null)

    val isEmpty: Boolean
        get() = connected && data?.isEmpty != false && overview?.scores?.isEmpty() != false
}

class HealthViewModel(
    private val repository: AventoRepository,
    private val errorMessage: (Throwable) -> String = {
        it.message ?: "Google Health konnte nicht geladen werden."
    },
) : ViewModel() {
    private val _state = MutableStateFlow(HealthUiState())
    val state: StateFlow<HealthUiState> = _state.asStateFlow()
    private var loadInProgress = false
    private var automaticSyncAttempted = false
    private var pendingForegroundCheck: Instant? = null

    init {
        refresh()
    }

    fun refresh() {
        if (loadInProgress) return
        loadInProgress = true
        viewModelScope.launch {
            val firstLoad = _state.value.connection == null && _state.value.connectionError == null
            _state.update {
                it.copy(
                    initialLoading = firstLoad,
                    refreshing = !firstLoad,
                    connectionError = null,
                )
            }
            reload()
            loadInProgress = false
            maybeStartAutomaticSync()
        }
    }

    fun onForeground(now: Instant = Instant.now()) {
        if (!automaticSyncAttempted) pendingForegroundCheck = now
        refresh()
    }

    fun startOAuth() {
        if (_state.value.connecting) return
        if (_state.value.connection?.enabled == false) {
            _state.update {
                it.copy(actionError = "Google Health ist auf diesem Avento-Server nicht aktiviert.")
            }
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(connecting = true, actionError = null, message = null) }
            runCatching {
                val connection = _state.value.connection
                repository.startHealthOAuth(
                    forceConsent = connection?.connected == true || connection?.status == "reauthorization_required",
                )
            }.onSuccess { start ->
                if (!isSafeHealthOAuthUrl(start.authorizationUrl, start.mockMode)) {
                    _state.update {
                        it.copy(
                            connecting = false,
                            actionError = "Die vom Server gelieferte Google-Anmeldeadresse ist nicht vertrauenswürdig.",
                        )
                    }
                    return@onSuccess
                }
                _state.update {
                    it.copy(
                        connecting = false,
                        oauthLaunch = HealthOAuthLaunch(start.authorizationUrl, start.mockMode),
                    )
                }
            }.onFailure { error ->
                _state.update { it.copy(connecting = false, actionError = errorMessage(error)) }
            }
        }
    }

    fun consumeOAuthLaunch() {
        _state.update { it.copy(oauthLaunch = null) }
    }

    fun oauthLaunchFailed() {
        _state.update {
            it.copy(
                oauthLaunch = null,
                actionError = "Die Google-Anmeldung konnte nicht im Browser geöffnet werden.",
            )
        }
    }

    fun synchronize(lookbackDays: Int? = null) {
        if (_state.value.syncing || !_state.value.connected) return
        viewModelScope.launch {
            _state.update { it.copy(syncing = true, actionError = null, message = null) }
            runCatching { repository.syncHealth(lookbackDays) }
                .onSuccess { result ->
                    reload(
                        notice = when (result.status.lowercase()) {
                            "succeeded" -> "Google-Health-Daten wurden synchronisiert."
                            "partial" -> "Die Synchronisation wurde mit Teilergebnissen abgeschlossen."
                            else -> "Synchronisationsstatus: ${result.status}."
                        },
                    )
                }
                .onFailure { error ->
                    _state.update { it.copy(syncing = false, actionError = errorMessage(error)) }
                }
        }
    }

    fun disconnect() {
        if (_state.value.disconnecting || !_state.value.hasConnection) return
        viewModelScope.launch {
            _state.update { it.copy(disconnecting = true, actionError = null, message = null) }
            runCatching { repository.disconnectHealth() }
                .onSuccess {
                    _state.value = HealthUiState(
                        initialLoading = false,
                        connection = HealthConnectionStatus(),
                        message = "Die Google-Health-Verbindung und die importierten Gesundheitsdaten wurden entfernt.",
                    )
                }
                .onFailure { error ->
                    _state.update { it.copy(disconnecting = false, actionError = errorMessage(error)) }
                }
        }
    }

    fun clearNotice() {
        _state.update { it.copy(actionError = null, message = null) }
    }

    private suspend fun reload(notice: String? = null) {
        val connectionResult = runCatching { repository.healthConnection() }
        val connection = connectionResult.getOrNull()
        if (connection == null) {
            _state.update {
                it.copy(
                    initialLoading = false,
                    refreshing = false,
                    syncing = false,
                    connectionError = errorMessage(requireNotNull(connectionResult.exceptionOrNull())),
                )
            }
            return
        }
        if (!connection.connected) {
            _state.update {
                it.copy(
                    initialLoading = false,
                    refreshing = false,
                    syncing = false,
                    connection = connection,
                    data = null,
                    overview = null,
                    connectionError = null,
                    dataError = null,
                    scoresError = null,
                    message = notice ?: it.message,
                )
            }
            return
        }

        val dataResult = runCatching { repository.healthData() }
        val scoresResult = runCatching { repository.healthScores() }
        _state.update {
            it.copy(
                initialLoading = false,
                refreshing = false,
                syncing = false,
                connection = connection,
                data = dataResult.getOrNull(),
                overview = scoresResult.getOrNull(),
                connectionError = null,
                dataError = dataResult.exceptionOrNull()?.let(errorMessage),
                scoresError = scoresResult.exceptionOrNull()?.let(errorMessage),
                message = notice ?: it.message,
            )
        }
    }

    private fun maybeStartAutomaticSync() {
        val now = pendingForegroundCheck ?: return
        pendingForegroundCheck = null
        val connection = _state.value.connection ?: return
        if (!connection.connected || connection.missingScopes.isNotEmpty() || automaticSyncAttempted) return
        automaticSyncAttempted = true
        if (shouldAutomaticallySyncHealth(connection, now)) synchronize()
    }
}

fun isSafeHealthOAuthUrl(value: String, mockMode: Boolean): Boolean {
    val uri = runCatching { URI(value) }.getOrNull() ?: return false
    val scheme = uri.scheme?.lowercase(Locale.ROOT) ?: return false
    val host = uri.host?.lowercase(Locale.ROOT)?.trimEnd('.') ?: return false
    if (!uri.isAbsolute || uri.rawUserInfo != null || uri.rawFragment != null) return false

    if (mockMode) {
        val localHost = host in setOf("localhost", "127.0.0.1", "::1", "[::1]")
        return localHost && scheme in setOf("http", "https") &&
            uri.path.orEmpty().endsWith("/health/oauth/callback")
    }

    return scheme == "https" &&
        host == "accounts.google.com" &&
        uri.path == "/o/oauth2/v2/auth"
}

fun shouldAutomaticallySyncHealth(
    connection: HealthConnectionStatus,
    now: Instant = Instant.now(),
    maximumAge: Duration = Duration.ofHours(6),
): Boolean {
    if (!connection.connected || connection.missingScopes.isNotEmpty()) return false
    val lastSync = connection.lastSyncAt?.let { value ->
        runCatching { Instant.parse(value) }
            .recoverCatching { OffsetDateTime.parse(value).toInstant() }
            .getOrNull()
    } ?: return true
    return lastSync.isBefore(now.minus(maximumAge))
}
