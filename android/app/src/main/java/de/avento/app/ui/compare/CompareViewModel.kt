package de.avento.app.ui.compare

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import de.avento.app.data.AventoRepository
import de.avento.app.data.model.Activity
import de.avento.app.data.model.ActivityFilters
import de.avento.app.data.model.CompareResponse
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class CompareUiState(
    val loading: Boolean = true,
    val comparing: Boolean = false,
    val activities: List<Activity> = emptyList(),
    val query: String = "",
    val selectedIds: Set<String> = emptySet(),
    val result: CompareResponse? = null,
    val error: String? = null,
) {
    val filteredActivities: List<Activity>
        get() {
            val needle = query.trim()
            return if (needle.isEmpty()) activities else activities.filter {
                it.title.orEmpty().contains(needle, ignoreCase = true) ||
                    it.originalFilename.orEmpty().contains(needle, ignoreCase = true)
            }
        }
}

class CompareViewModel(
    private val repository: AventoRepository,
    private val errorMessage: (Throwable) -> String,
) : ViewModel() {
    private val _state = MutableStateFlow(CompareUiState())
    val state: StateFlow<CompareUiState> = _state.asStateFlow()

    init { loadActivities() }

    fun updateQuery(value: String) = _state.update { it.copy(query = value) }

    fun toggle(activityId: String) {
        _state.update { state ->
            val selected = state.selectedIds.toMutableSet()
            if (!selected.add(activityId)) selected.remove(activityId)
            if (selected.size > 10) {
                state.copy(error = "Es können höchstens zehn Aktivitäten verglichen werden.")
            } else {
                state.copy(selectedIds = selected, result = null, error = null)
            }
        }
    }

    fun clearSelection() = _state.update { it.copy(selectedIds = emptySet(), result = null, error = null) }

    fun compare() {
        val ids = _state.value.selectedIds.toList()
        if (ids.size < 2) {
            _state.update { it.copy(error = "Wähle mindestens zwei Aktivitäten aus.") }
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(comparing = true, error = null) }
            runCatching { repository.compareActivities(ids) }
                .onSuccess { result -> _state.update { it.copy(comparing = false, result = result) } }
                .onFailure { failure -> _state.update { it.copy(comparing = false, error = errorMessage(failure)) } }
        }
    }

    fun loadActivities() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            runCatching { repository.activities(ActivityFilters(limit = 200)) }
                .onSuccess { response -> _state.update { it.copy(loading = false, activities = response.items) } }
                .onFailure { failure -> _state.update { it.copy(loading = false, error = errorMessage(failure)) } }
        }
    }

    fun clearError() = _state.update { it.copy(error = null) }
}
