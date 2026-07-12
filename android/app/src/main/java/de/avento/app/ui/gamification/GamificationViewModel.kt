package de.avento.app.ui.gamification

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import de.avento.app.data.AventoRepository
import de.avento.app.data.model.GamificationChallenge
import de.avento.app.data.model.GamificationGoal
import de.avento.app.data.model.GamificationGoalRequest
import de.avento.app.data.model.GamificationOverview
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class GamificationUiState(
    val loading: Boolean = true,
    val saving: Boolean = false,
    val overview: GamificationOverview? = null,
    val goalEditorOpen: Boolean = false,
    val editingGoal: GamificationGoal? = null,
    val error: String? = null,
    val message: String? = null,
)

class GamificationViewModel(
    private val repository: AventoRepository,
    private val errorMessage: (Throwable) -> String,
) : ViewModel() {
    private val _state = MutableStateFlow(GamificationUiState())
    val state: StateFlow<GamificationUiState> = _state.asStateFlow()

    init { load() }

    fun load() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            runCatching { repository.gamificationOverview() }
                .onSuccess { overview -> _state.update { it.copy(loading = false, overview = overview) } }
                .onFailure { failure -> _state.update { it.copy(loading = false, error = errorMessage(failure)) } }
        }
    }

    fun beginCreate() = _state.update { it.copy(goalEditorOpen = true, editingGoal = null, error = null) }
    fun beginEdit(goal: GamificationGoal) = _state.update { it.copy(goalEditorOpen = true, editingGoal = goal, error = null) }
    fun closeEditor() = _state.update { it.copy(goalEditorOpen = false, editingGoal = null) }

    fun saveGoal(
        id: String?,
        request: GamificationGoalRequest,
        onDone: () -> Unit,
    ) {
        if (_state.value.saving) return
        viewModelScope.launch {
            _state.update { it.copy(saving = true, error = null) }
            runCatching {
                if (id == null) repository.createGamificationGoal(request)
                else repository.updateGamificationGoal(id, request)
            }.onSuccess {
                _state.update { it.copy(saving = false, goalEditorOpen = false, editingGoal = null, message = "Ziel gespeichert.") }
                onDone()
                load()
            }.onFailure { failure -> _state.update { it.copy(saving = false, error = errorMessage(failure)) } }
        }
    }

    fun deleteGoal(goal: GamificationGoal) {
        viewModelScope.launch {
            _state.update { it.copy(saving = true, error = null) }
            runCatching { repository.deleteGamificationGoal(goal.id) }
                .onSuccess {
                    _state.update { it.copy(saving = false, message = "Ziel gelöscht.") }
                    load()
                }
                .onFailure { failure -> _state.update { it.copy(saving = false, error = errorMessage(failure)) } }
        }
    }

    fun accept(challenge: GamificationChallenge) = updateChallenge(challenge, accept = true)
    fun decline(challenge: GamificationChallenge) = updateChallenge(challenge, accept = false)

    fun clearNotice() = _state.update { it.copy(error = null, message = null) }

    private fun updateChallenge(challenge: GamificationChallenge, accept: Boolean) {
        viewModelScope.launch {
            _state.update { it.copy(saving = true, error = null) }
            runCatching {
                if (accept) repository.acceptGamificationChallenge(challenge.id)
                else repository.declineGamificationChallenge(challenge.id)
            }.onSuccess {
                _state.update {
                    it.copy(
                        saving = false,
                        message = if (accept) "Herausforderung angenommen." else "Vorschlag ausgeblendet.",
                    )
                }
                load()
            }.onFailure { failure -> _state.update { it.copy(saving = false, error = errorMessage(failure)) } }
        }
    }
}
