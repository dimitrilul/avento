package de.avento.app.ui.insights

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import de.avento.app.data.AventoRepository
import de.avento.app.data.model.LongTermInsights
import de.avento.app.data.model.PeriodReview
import java.time.LocalDate
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class InsightsUiState(
    val loading: Boolean = true,
    val insights: LongTermInsights? = null,
    val review: PeriodReview? = null,
    val year: Int = LocalDate.now().year,
    val season: String = "year",
    val error: String? = null,
)

class InsightsViewModel(
    private val repository: AventoRepository,
    private val errorMessage: (Throwable) -> String,
) : ViewModel() {
    private val _state = MutableStateFlow(InsightsUiState())
    val state: StateFlow<InsightsUiState> = _state.asStateFlow()

    init { load() }

    fun load() {
        val current = _state.value
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            runCatching {
                val insights = repository.longTermInsights(null, null)
                val review = repository.periodReview(current.year, current.season)
                insights to review
            }.onSuccess { (insights, review) -> _state.update { it.copy(loading = false, insights = insights, review = review) } }
                .onFailure { failure -> _state.update { it.copy(loading = false, error = errorMessage(failure)) } }
        }
    }

    fun setYear(value: String) {
        value.toIntOrNull()?.takeIf { it in 1900..9998 }?.let { _state.update { state -> state.copy(year = it) } }
    }

    fun setSeason(value: String) {
        _state.update { it.copy(season = value) }
        load()
    }
}
