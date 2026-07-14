package de.avento.app

import android.app.Application
import android.net.Uri
import de.avento.app.data.AventoRepository
import de.avento.app.data.DefaultAventoRepository
import de.avento.app.data.network.NetworkProvider
import de.avento.app.data.security.EncryptedTokenStore
import de.avento.app.settings.ServerConfigStore
import de.avento.app.settings.normalizeServerUrl
import com.squareup.moshi.Moshi
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import org.maplibre.android.MapLibre

data class PendingImport(val uri: Uri, val displayName: String? = null)

sealed interface ServerState {
    data object Loading : ServerState
    data object Missing : ServerState
    data class Connected(
        val serverUrl: String,
        val repository: AventoRepository,
        val errorMoshi: Moshi,
    ) : ServerState
}

class AppContainer(application: Application) {
    private val tokenStore = EncryptedTokenStore(application)
    private val serverConfig = ServerConfigStore(application)
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val _serverState = MutableStateFlow<ServerState>(ServerState.Loading)
    val serverState: StateFlow<ServerState> = _serverState

    private val _pendingImport = MutableStateFlow<PendingImport?>(null)
    val pendingImport: StateFlow<PendingImport?> = _pendingImport

    init {
        scope.launch {
            serverConfig.serverUrl.collectLatest { url ->
                _serverState.value = if (url == null) ServerState.Missing else connected(url)
            }
        }
    }

    fun configureServer(input: String): Result<Unit> = runCatching {
        val normalized = normalizeServerUrl(input)
        scope.launch {
            tokenStore.clear()
            serverConfig.save(normalized)
        }
    }

    fun forgetServer() {
        scope.launch {
            tokenStore.clear()
            serverConfig.clear()
        }
    }

    private fun connected(url: String): ServerState.Connected {
        val network = NetworkProvider(tokenStore, url)
        return ServerState.Connected(
            serverUrl = url,
            repository = DefaultAventoRepository(
                publicApi = network.publicApi,
                api = network.authenticatedApi,
                tokenStore = tokenStore,
            ),
            errorMoshi = network.moshi,
        )
    }

    fun offerImport(import: PendingImport) {
        _pendingImport.value = import
    }

    fun consumeImport() {
        _pendingImport.value = null
    }
}

class AventoApplication : Application() {
    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        MapLibre.getInstance(this)
        container = AppContainer(this)
    }
}
