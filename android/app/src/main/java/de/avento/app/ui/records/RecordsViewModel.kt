package de.avento.app.ui.records

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import de.avento.app.data.AventoRepository
import de.avento.app.data.model.PersonalRecords
import de.avento.app.data.model.ActivityPhoto
import de.avento.app.share.AchievementInfo
import de.avento.app.share.OverlayShareContent
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class RecordsUiState(
    val loading: Boolean = true,
    val records: PersonalRecords? = null,
    val error: String? = null,
    val shareContent: OverlayShareContent.ActivityContent? = null,
    val sharePhotos: List<ActivityPhoto> = emptyList(),
    val shareLoading: Boolean = false,
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

    fun prepareShare(activityId: String, achievement: AchievementInfo) {
        viewModelScope.launch {
            _state.update { it.copy(shareLoading = true, error = null) }
            runCatching {
                coroutineScope {
                    val activity = async { repository.activity(activityId) }
                    val track = async { runCatching { repository.track(activityId) }.getOrNull() }
                    val photos = async { runCatching { repository.activityPhotos(activityId) }.getOrNull()?.items.orEmpty() }
                    OverlayShareContent.ActivityContent(activity.await(), track.await(), achievement) to photos.await()
                }
            }.onSuccess { (content, photos) -> _state.update { it.copy(shareLoading = false, shareContent = content, sharePhotos = photos) } }
                .onFailure { failure -> _state.update { it.copy(shareLoading = false, error = errorMessage(failure)) } }
        }
    }

    fun closeShare() = _state.update { it.copy(shareContent = null, sharePhotos = emptyList()) }
    suspend fun photoBytes(photo: ActivityPhoto): ByteArray = repository.activityPhotoBytes(photo)
}
