package de.avento.app

import android.app.Application
import android.net.Uri
import de.avento.app.data.AventoRepository
import de.avento.app.data.DefaultAventoRepository
import de.avento.app.data.network.NetworkProvider
import de.avento.app.data.security.EncryptedTokenStore
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

data class PendingImport(val uri: Uri, val displayName: String? = null)

class AppContainer(application: Application) {
    private val tokenStore = EncryptedTokenStore(application)
    private val network = NetworkProvider(tokenStore)

    val repository: AventoRepository = DefaultAventoRepository(
        publicApi = network.publicApi,
        api = network.authenticatedApi,
        tokenStore = tokenStore,
    )
    val errorMoshi = network.moshi

    private val _pendingImport = MutableStateFlow<PendingImport?>(null)
    val pendingImport: StateFlow<PendingImport?> = _pendingImport

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
        container = AppContainer(this)
    }
}
