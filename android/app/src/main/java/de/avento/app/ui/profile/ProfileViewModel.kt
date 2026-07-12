package de.avento.app.ui.profile

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import de.avento.app.data.AventoRepository
import de.avento.app.data.model.Profile
import de.avento.app.data.model.ProfileUpdate
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ProfileUiState(
    val loading: Boolean = true,
    val saving: Boolean = false,
    val profile: Profile? = null,
    val message: String? = null,
    val error: String? = null,
)

class ProfileViewModel(
    private val repository: AventoRepository,
    private val errorMessage: (Throwable) -> String,
) : ViewModel() {
    private val _state = MutableStateFlow(ProfileUiState())
    val state: StateFlow<ProfileUiState> = _state.asStateFlow()

    init { load() }

    fun load() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            runCatching { repository.profile() }
                .onSuccess { profile -> _state.update { it.copy(loading = false, profile = profile) } }
                .onFailure { failure -> _state.update { it.copy(loading = false, error = errorMessage(failure)) } }
        }
    }

    fun save(update: ProfileUpdate) {
        viewModelScope.launch {
            _state.update { it.copy(saving = true, error = null) }
            runCatching { repository.updateProfile(update) }
                .onSuccess { profile -> _state.update { it.copy(saving = false, profile = profile, message = "Profil gespeichert.") } }
                .onFailure { failure -> _state.update { it.copy(saving = false, error = errorMessage(failure)) } }
        }
    }

    fun uploadAvatar(bytes: ByteArray, name: String, contentType: String) {
        viewModelScope.launch {
            _state.update { it.copy(saving = true, error = null) }
            runCatching { repository.uploadAvatar(bytes, name, contentType) }
                .onSuccess { profile -> _state.update { it.copy(saving = false, profile = profile, message = "Profilbild gespeichert.") } }
                .onFailure { failure -> _state.update { it.copy(saving = false, error = errorMessage(failure)) } }
        }
    }

    fun deleteAvatar() {
        viewModelScope.launch {
            _state.update { it.copy(saving = true, error = null) }
            runCatching { repository.deleteAvatar() }
                .onSuccess { profile -> _state.update { it.copy(saving = false, profile = profile, message = "Profilbild entfernt.") } }
                .onFailure { failure -> _state.update { it.copy(saving = false, error = errorMessage(failure)) } }
        }
    }

    fun changePassword(current: String, next: String, confirmation: String) {
        viewModelScope.launch {
            _state.update { it.copy(saving = true, error = null) }
            runCatching {
                require(current.isNotBlank()) { "Bitte gib dein aktuelles Passwort ein." }
                require(next.length >= 10) { "Das neue Passwort muss mindestens 10 Zeichen lang sein." }
                require(next == confirmation) { "Die Passwörter stimmen nicht überein." }
                repository.changePassword(current, next)
            }.onSuccess { _state.update { it.copy(saving = false, message = "Passwort geändert.") } }
                .onFailure { failure -> _state.update { it.copy(saving = false, error = errorMessage(failure)) } }
        }
    }

    fun clearNotice() = _state.update { it.copy(error = null, message = null) }
}
