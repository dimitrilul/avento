package de.avento.app.ui.statistics

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import de.avento.app.data.AventoRepository
import de.avento.app.data.model.OverviewStatistics
import de.avento.app.data.model.StatisticsRange
import java.time.LocalDate
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class StatisticsUiState(
    val loading: Boolean = true,
    val preset: String = "90",
    val dateFrom: String = LocalDate.now().minusDays(89).toString(),
    val dateTo: String = LocalDate.now().toString(),
    val granularity: String = "auto",
    val statistics: OverviewStatistics? = null,
    val error: String? = null,
)

class StatisticsViewModel(
    private val repository: AventoRepository,
    private val errorMessage: (Throwable) -> String,
    private val today: () -> LocalDate = LocalDate::now,
) : ViewModel() {
    private val _state = MutableStateFlow(
        StatisticsUiState(
            dateFrom = today().minusDays(89).toString(),
            dateTo = today().toString(),
        ),
    )
    val state: StateFlow<StatisticsUiState> = _state.asStateFlow()

    init { load() }

    fun setPreset(preset: String) {
        val end = today()
        val start = when (preset) {
            "30" -> end.minusDays(29)
            "90" -> end.minusDays(89)
            "year" -> end.withDayOfYear(1)
            "all" -> null
            else -> return
        }
        _state.update {
            it.copy(
                preset = preset,
                dateFrom = start?.toString().orEmpty(),
                dateTo = if (start == null) "" else end.toString(),
            )
        }
        load()
    }

    fun updateDateFrom(value: String) = _state.update { it.copy(dateFrom = value, preset = "custom") }
    fun updateDateTo(value: String) = _state.update { it.copy(dateTo = value, preset = "custom") }
    fun setGranularity(value: String) {
        _state.update { it.copy(granularity = value) }
        load()
    }

    fun load() {
        val current = _state.value
        val from = parseDate(current.dateFrom)
        val to = parseDate(current.dateTo)
        if (current.dateFrom.isNotBlank() && from == null || current.dateTo.isNotBlank() && to == null) {
            _state.update { it.copy(error = "Bitte verwende Datumswerte im Format JJJJ-MM-TT.") }
            return
        }
        if (from != null && to != null && to < from) {
            _state.update { it.copy(error = "Das Enddatum muss nach dem Startdatum liegen.") }
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            runCatching {
                repository.statistics(
                    StatisticsRange(
                        dateFrom = current.dateFrom.ifBlank { null },
                        dateTo = current.dateTo.ifBlank { null },
                        granularity = current.granularity,
                    ),
                )
            }.onSuccess { result ->
                _state.update { it.copy(loading = false, statistics = result) }
            }.onFailure { failure ->
                _state.update { it.copy(loading = false, error = errorMessage(failure)) }
            }
        }
    }

    fun clearError() = _state.update { it.copy(error = null) }

    private fun parseDate(value: String): LocalDate? =
        value.takeIf(String::isNotBlank)?.let { runCatching { LocalDate.parse(it) }.getOrNull() }
}
