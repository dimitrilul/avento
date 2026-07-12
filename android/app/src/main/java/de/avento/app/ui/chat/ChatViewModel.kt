package de.avento.app.ui.chat

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import de.avento.app.data.AventoRepository
import de.avento.app.data.model.ChatHistoryItem
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ChatUiState(
    val sending: Boolean = false,
    val messages: List<ChatHistoryItem> = emptyList(),
    val error: String? = null,
)

class ChatViewModel(
    private val repository: AventoRepository,
    private val errorMessage: (Throwable) -> String,
) : ViewModel() {
    private val _state = MutableStateFlow(ChatUiState())
    val state: StateFlow<ChatUiState> = _state.asStateFlow()

    fun send(text: String) {
        val message = text.trim()
        if (message.isEmpty() || _state.value.sending) return
        val history = _state.value.messages
        _state.update { it.copy(sending = true, error = null, messages = history + ChatHistoryItem("user", message)) }
        viewModelScope.launch {
            runCatching { repository.chat(message, history, null) }
                .onSuccess { response ->
                    _state.update { it.copy(sending = false, messages = it.messages + ChatHistoryItem("assistant", response.answer)) }
                }
                .onFailure { failure -> _state.update { it.copy(sending = false, error = errorMessage(failure)) } }
        }
    }

    fun clearError() = _state.update { it.copy(error = null) }
}
