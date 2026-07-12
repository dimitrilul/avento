package de.avento.app.ui.detail

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import de.avento.app.data.AventoRepository
import de.avento.app.data.model.Activity
import de.avento.app.data.model.ActivityTrack
import de.avento.app.data.model.ActivityPhoto
import de.avento.app.data.model.SummaryResponse
import de.avento.app.data.model.WeatherResponse
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class DetailUiState(
    val loading: Boolean = true,
    val saving: Boolean = false,
    val refreshingWeather: Boolean = false,
    val generatingSummary: Boolean = false,
    val uploadingPhoto: Boolean = false,
    val activity: Activity? = null,
    val track: ActivityTrack? = null,
    val weather: WeatherResponse? = null,
    val summary: SummaryResponse? = null,
    val photos: List<ActivityPhoto> = emptyList(),
    val error: String? = null,
    val message: String? = null,
)

class DetailViewModel(
    private val activityId: String,
    private val repository: AventoRepository,
    private val errorMessage: (Throwable) -> String,
) : ViewModel() {
    private val _state = MutableStateFlow(DetailUiState())
    val state: StateFlow<DetailUiState> = _state.asStateFlow()

    init { load() }

    fun load() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true, error = null) }
            runCatching {
                coroutineScope {
                    val activity = async { repository.activity(activityId) }
                    val track = async { runCatching { repository.track(activityId) }.getOrNull() }
                    val weather = async { runCatching { repository.weather(activityId) }.getOrNull() }
                    val summary = async { runCatching { repository.summary(activityId) }.getOrNull() }
                    val photos = async { runCatching { repository.activityPhotos(activityId) }.getOrNull()?.items.orEmpty() }
                    Loaded(activity.await(), track.await(), weather.await(), summary.await(), photos.await())
                }
            }.onSuccess { loaded ->
                _state.update {
                    it.copy(
                        loading = false,
                        activity = loaded.activity,
                        track = loaded.track,
                        weather = loaded.weather,
                        summary = loaded.summary,
                        photos = loaded.photos,
                    )
                }
            }.onFailure { failure ->
                _state.update { it.copy(loading = false, error = errorMessage(failure)) }
            }
        }
    }

    fun refreshWeather() = launchAction(
        start = { copy(refreshingWeather = true, error = null) },
        block = { repository.refreshWeather(activityId) },
        success = { weather -> copy(refreshingWeather = false, weather = weather, message = "Wetter wurde aktualisiert.") },
        failure = { copy(refreshingWeather = false, error = errorMessage(it)) },
    )

    fun generateSummary(force: Boolean = false) = launchAction(
        start = { copy(generatingSummary = true, error = null) },
        block = { repository.generateSummary(activityId, force) },
        success = { summary -> copy(generatingSummary = false, summary = summary, message = "KI-Auswertung ist bereit.") },
        failure = { copy(generatingSummary = false, error = errorMessage(it)) },
    )

    fun reanalyze() = launchAction(
        start = { copy(saving = true, error = null) },
        block = { repository.reanalyzeActivity(activityId) },
        success = { activity -> copy(saving = false, activity = activity, message = "Aktivität wurde neu analysiert.") },
        failure = { copy(saving = false, error = errorMessage(it)) },
    )

    fun uploadPhoto(bytes: ByteArray, fileName: String, contentType: String, caption: String? = null) {
        if (_state.value.uploadingPhoto) return
        viewModelScope.launch {
            _state.update { it.copy(uploadingPhoto = true, error = null) }
            runCatching { repository.uploadActivityPhoto(activityId, bytes, fileName, contentType, caption) }
                .onSuccess { photo -> _state.update { it.copy(uploadingPhoto = false, photos = it.photos + photo, message = "Foto gespeichert.") } }
                .onFailure { failure -> _state.update { it.copy(uploadingPhoto = false, error = errorMessage(failure)) } }
        }
    }

    fun deletePhoto(photo: ActivityPhoto) {
        viewModelScope.launch {
            _state.update { it.copy(saving = true, error = null) }
            runCatching { repository.deleteActivityPhoto(activityId, photo.id) }
                .onSuccess { _state.update { it.copy(saving = false, photos = it.photos.filterNot { item -> item.id == photo.id }, message = "Foto gelöscht.") } }
                .onFailure { failure -> _state.update { it.copy(saving = false, error = errorMessage(failure)) } }
        }
    }

    suspend fun photoBytes(photo: ActivityPhoto): ByteArray = repository.activityPhotoBytes(photo)

    fun save(title: String?, type: String?, notes: String?, hydrationMilliliters: Int?, onSaved: () -> Unit) = launchAction(
        start = { copy(saving = true, error = null) },
        block = { repository.updateActivity(activityId, title, type, notes, hydrationMilliliters) },
        success = { activity -> copy(saving = false, activity = activity, message = "Aktivität gespeichert.") },
        failure = { copy(saving = false, error = errorMessage(it)) },
        afterSuccess = onSaved,
    )

    fun delete(onDeleted: () -> Unit) {
        if (_state.value.saving) return
        viewModelScope.launch {
            _state.update { it.copy(saving = true, error = null) }
            runCatching { repository.deleteActivity(activityId) }
                .onSuccess { onDeleted() }
                .onFailure { failure ->
                    _state.update { it.copy(saving = false, error = errorMessage(failure)) }
                }
        }
    }

    fun clearNotice() = _state.update { it.copy(error = null, message = null) }

    private fun <T> launchAction(
        start: DetailUiState.() -> DetailUiState,
        block: suspend () -> T,
        success: DetailUiState.(T) -> DetailUiState,
        failure: DetailUiState.(Throwable) -> DetailUiState,
        afterSuccess: () -> Unit = {},
    ) {
        viewModelScope.launch {
            _state.update(start)
            runCatching { block() }
                .onSuccess { value ->
                    _state.update { it.success(value) }
                    afterSuccess()
                }
                .onFailure { throwable -> _state.update { it.failure(throwable) } }
        }
    }

    private data class Loaded(
        val activity: Activity,
        val track: ActivityTrack?,
        val weather: WeatherResponse?,
        val summary: SummaryResponse?,
        val photos: List<ActivityPhoto>,
    )
}
