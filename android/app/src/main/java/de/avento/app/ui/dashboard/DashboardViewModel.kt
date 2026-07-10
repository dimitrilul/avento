package de.avento.app.ui.dashboard

import android.content.ContentResolver
import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import de.avento.app.data.AventoRepository
import de.avento.app.data.model.Activity
import de.avento.app.data.model.OverviewStatistics
import de.avento.app.data.model.Profile
import de.avento.app.util.displayName
import de.avento.app.util.readTcx
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

data class DashboardUiState(
    val loading: Boolean = true,
    val importing: Boolean = false,
    val activities: List<Activity> = emptyList(),
    val statistics: OverviewStatistics? = null,
    val profile: Profile? = null,
    val error: String? = null,
    val message: String? = null,
)

class DashboardViewModel(
    private val repository: AventoRepository,
    private val errorMessage: (Throwable) -> String,
) : ViewModel() {
    private val _state = MutableStateFlow(DashboardUiState())
    val state: StateFlow<DashboardUiState> = _state.asStateFlow()

    init { refresh() }

    fun refresh(query: String? = null) {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            runCatching {
                val activities = async { repository.activities(query) }
                val statistics = async { repository.statistics() }
                val profile = async { runCatching { repository.profile() }.getOrNull() }
                Triple(activities.await(), statistics.await(), profile.await())
            }.onSuccess { (activities, statistics, profile) ->
                _state.update {
                    it.copy(
                        loading = false,
                        activities = activities.items,
                        statistics = statistics,
                        profile = profile ?: it.profile,
                    )
                }
            }.onFailure { failure ->
                _state.update { it.copy(loading = false, error = errorMessage(failure)) }
            }
        }
    }

    fun upload(
        resolver: ContentResolver,
        uri: Uri,
        fallbackName: String?,
        title: String?,
        type: String?,
        notes: String?,
        onSuccess: (Activity) -> Unit,
    ) {
        if (_state.value.importing) return
        viewModelScope.launch {
            _state.update { it.copy(importing = true, error = null) }
            runCatching {
                val (bytes, name) = withContext(Dispatchers.IO) {
                    resolver.readTcx(uri) to (resolver.displayName(uri) ?: fallbackName ?: "aktivitaet.tcx")
                }
                require(name.lowercase().endsWith(".tcx")) { "Bitte wähle eine TCX-Datei aus." }
                repository.uploadTcx(bytes, name, title, type, notes)
            }.onSuccess { activity ->
                _state.update {
                    it.copy(
                        importing = false,
                        message = "${activity.title ?: "Aktivität"} wurde importiert.",
                    )
                }
                refresh()
                onSuccess(activity)
            }.onFailure { failure ->
                _state.update { it.copy(importing = false, error = errorMessage(failure)) }
            }
        }
    }

    fun logout(onComplete: () -> Unit) {
        viewModelScope.launch {
            runCatching { repository.logout() }
            onComplete()
        }
    }

    fun clearNotice() = _state.update { it.copy(error = null, message = null) }
}
