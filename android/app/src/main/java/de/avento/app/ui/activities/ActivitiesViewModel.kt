package de.avento.app.ui.activities

import android.content.ContentResolver
import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import de.avento.app.data.AventoRepository
import de.avento.app.data.model.Activity
import de.avento.app.data.model.ActivityFilters
import de.avento.app.util.displayName
import de.avento.app.util.readActivity
import java.time.LocalDate
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

data class ActivitiesUiState(
    val loading: Boolean = true,
    val importing: Boolean = false,
    val activities: List<Activity> = emptyList(),
    val total: Int = 0,
    val filters: ActivityFilters = ActivityFilters(limit = PAGE_SIZE),
    val error: String? = null,
    val message: String? = null,
) {
    val page: Int get() = filters.offset / filters.limit + 1
    val pageCount: Int get() = ((total + filters.limit - 1) / filters.limit).coerceAtLeast(1)
    val canGoBack: Boolean get() = filters.offset > 0
    val canGoForward: Boolean get() = filters.offset + filters.limit < total

    companion object { const val PAGE_SIZE = 12 }
}

private const val PAGE_SIZE = ActivitiesUiState.PAGE_SIZE

class ActivitiesViewModel(
    private val repository: AventoRepository,
    private val errorMessage: (Throwable) -> String,
) : ViewModel() {
    private val _state = MutableStateFlow(ActivitiesUiState())
    val state: StateFlow<ActivitiesUiState> = _state.asStateFlow()

    init { load() }

    fun updateQuery(value: String) = updateFilters { copy(query = value) }
    fun updateType(value: String) = updateFilters { copy(type = value) }
    fun updateDateFrom(value: String) = updateFilters { copy(dateFrom = value) }
    fun updateDateTo(value: String) = updateFilters { copy(dateTo = value) }

    fun applyFilters() {
        val filters = _state.value.filters
        val validation = validateDates(filters.dateFrom, filters.dateTo)
        if (validation != null) {
            _state.update { it.copy(error = validation) }
            return
        }
        _state.update { it.copy(filters = it.filters.copy(offset = 0)) }
        load()
    }

    fun resetFilters() {
        _state.update { it.copy(filters = ActivityFilters(limit = PAGE_SIZE)) }
        load()
    }

    fun nextPage() {
        if (!_state.value.canGoForward) return
        _state.update { it.copy(filters = it.filters.copy(offset = it.filters.offset + it.filters.limit)) }
        load()
    }

    fun previousPage() {
        if (!_state.value.canGoBack) return
        _state.update {
            it.copy(filters = it.filters.copy(offset = (it.filters.offset - it.filters.limit).coerceAtLeast(0)))
        }
        load()
    }

    fun refresh() = load()

    fun upload(
        resolver: ContentResolver,
        uri: Uri,
        title: String?,
        type: String?,
        notes: String?,
        hydration: String?,
        onSuccess: (Activity) -> Unit,
    ) {
        if (_state.value.importing) return
        viewModelScope.launch {
            _state.update { it.copy(importing = true, error = null) }
            runCatching {
                val hydrationMl = hydration?.trim()?.takeIf(String::isNotEmpty)?.toIntOrNull()
                require(hydration.isNullOrBlank() || hydrationMl != null) { "Die Trinkmenge muss eine ganze Zahl sein." }
                val (bytes, name) = withContext(Dispatchers.IO) {
                    resolver.readActivity(uri) to (resolver.displayName(uri) ?: "aktivitaet.tcx")
                }
                require(name.lowercase().endsWith(".tcx") || name.lowercase().endsWith(".fit") || name.lowercase().endsWith(".gpx")) { "Bitte wähle eine TCX-, FIT- oder GPX-Datei aus." }
                repository.uploadTcx(bytes, name, title, type, notes, hydrationMl)
            }.onSuccess { activity ->
                _state.update { it.copy(importing = false, message = "${activity.title ?: "Aktivität"} wurde importiert.") }
                load()
                onSuccess(activity)
            }.onFailure { failure ->
                _state.update { it.copy(importing = false, error = errorMessage(failure)) }
            }
        }
    }

    fun clearNotice() = _state.update { it.copy(error = null, message = null) }

    private fun load() {
        viewModelScope.launch {
            val filters = _state.value.filters
            _state.update { it.copy(loading = true, error = null) }
            runCatching { repository.activities(filters) }
                .onSuccess { response ->
                    _state.update {
                        it.copy(
                            loading = false,
                            activities = response.items,
                            total = response.total,
                            filters = it.filters.copy(offset = response.offset, limit = response.limit),
                        )
                    }
                }
                .onFailure { failure ->
                    _state.update { it.copy(loading = false, error = errorMessage(failure)) }
                }
        }
    }

    private fun updateFilters(block: ActivityFilters.() -> ActivityFilters) {
        _state.update { it.copy(filters = it.filters.block()) }
    }

    private fun validateDates(from: String, to: String): String? {
        val start = from.takeIf(String::isNotBlank)?.let { runCatching { LocalDate.parse(it) }.getOrNull() }
        val end = to.takeIf(String::isNotBlank)?.let { runCatching { LocalDate.parse(it) }.getOrNull() }
        if (from.isNotBlank() && start == null || to.isNotBlank() && end == null) {
            return "Bitte verwende Datumswerte im Format JJJJ-MM-TT."
        }
        if (start != null && end != null && end < start) return "Das Enddatum muss nach dem Startdatum liegen."
        return null
    }
}
