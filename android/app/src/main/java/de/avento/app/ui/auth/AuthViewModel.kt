package de.avento.app.ui.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import de.avento.app.data.AventoRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class AuthUiState(
    val loading: Boolean = false,
    val error: String? = null,
)

class AuthViewModel(
    private val repository: AventoRepository,
    private val errorMessage: (Throwable) -> String = { it.message ?: "Anmeldung fehlgeschlagen." },
) : ViewModel() {
    private val _state = MutableStateFlow(AuthUiState())
    val state: StateFlow<AuthUiState> = _state.asStateFlow()

    fun login(email: String, password: String, onSuccess: () -> Unit) = submit {
        validate(email, password)
        repository.login(email.trim(), password)
        onSuccess()
    }

    fun register(
        email: String,
        password: String,
        displayName: String,
        inviteToken: String,
        onSuccess: () -> Unit,
    ) = submit {
        validate(email, password)
        require(displayName.isNotBlank()) { "Bitte gib deinen Namen ein." }
        require(inviteToken.isNotBlank()) { "Bitte gib den Einladungscode ein." }
        repository.register(email.trim(), password, displayName.trim(), inviteToken.trim())
        onSuccess()
    }

    fun bootstrap(
        email: String,
        password: String,
        displayName: String,
        bootstrapCode: String,
        onSuccess: () -> Unit,
    ) = submit {
        validate(email, password)
        require(displayName.isNotBlank()) { "Bitte gib deinen Namen ein." }
        require(bootstrapCode.isNotBlank()) { "Bitte gib den Einrichtungscode ein." }
        repository.bootstrap(email.trim(), password, displayName.trim(), bootstrapCode.trim())
        onSuccess()
    }

    fun resetPassword(
        token: String,
        newPassword: String,
        confirmation: String,
        onSuccess: () -> Unit,
    ) = submit {
        require(token.isNotBlank()) { "Bitte gib den Reset-Token ein." }
        validateNewPassword(newPassword, confirmation)
        repository.resetPassword(token.trim(), newPassword)
        onSuccess()
    }

    fun changePassword(
        currentPassword: String,
        newPassword: String,
        confirmation: String,
        onSuccess: () -> Unit,
    ) = submit {
        require(currentPassword.isNotBlank()) { "Bitte gib dein aktuelles Passwort ein." }
        require(currentPassword != newPassword) { "Das neue Passwort muss sich vom aktuellen unterscheiden." }
        validateNewPassword(newPassword, confirmation)
        repository.changePassword(currentPassword, newPassword)
        onSuccess()
    }

    fun clearError() = _state.update { it.copy(error = null) }

    private fun submit(block: suspend () -> Unit) {
        if (_state.value.loading) return
        viewModelScope.launch {
            _state.value = AuthUiState(loading = true)
            runCatching { block() }
                .onSuccess { _state.value = AuthUiState() }
                .onFailure { _state.value = AuthUiState(error = errorMessage(it)) }
        }
    }

    private fun validate(email: String, password: String) {
        require('@' in email && email.substringAfter('@').contains('.')) {
            "Bitte gib eine gültige E-Mail-Adresse ein."
        }
        require(password.length >= 10) { "Das Passwort muss mindestens 10 Zeichen lang sein." }
    }

    private fun validateNewPassword(password: String, confirmation: String) {
        require(password.length >= 10) { "Das neue Passwort muss mindestens 10 Zeichen lang sein." }
        require(password == confirmation) { "Die eingegebenen Passwörter stimmen nicht überein." }
    }
}
