package de.avento.app.ui.records

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import de.avento.app.data.AventoRepository
import de.avento.app.data.model.PersonalRecords
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class RecordsUiState(
    val loading: Boolean = true,
    val records: PersonalRecords? = null,
    val error: String? = null,
)

class RecordsViewModel(
    private val repository: AventoRepository,
    private val errorMessage: (Throwable) -> String,
) : ViewModel() {
    private val _state = MutableStateFlow(RecordsUiState())
    val state: StateFlow<RecordsUiState> = _state.asStateFlow()

    init { load() }

    fun load() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            runCatching { repository.personalRecords() }
                .onSuccess { records -> _state.update { it.copy(loading = false, records = records) } }
                .onFailure { failure -> _state.update { it.copy(loading = false, error = errorMessage(failure)) } }
        }
    }
}
