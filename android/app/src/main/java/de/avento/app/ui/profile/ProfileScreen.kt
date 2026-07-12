package de.avento.app.ui.profile

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Upload
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import de.avento.app.data.model.ProfileUpdate
import de.avento.app.ui.components.AventoTopBar
import de.avento.app.ui.components.ErrorPane
import de.avento.app.ui.components.LoadingPane
import de.avento.app.ui.components.ProfileAvatar
import de.avento.app.util.readAvatar
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@Composable
fun ProfileScreen(viewModel: ProfileViewModel) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val profile = state.profile
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val snackbar = remember { SnackbarHostState() }
    var displayName by rememberSaveable(profile?.id) { mutableStateOf(profile?.displayName.orEmpty()) }
    var hrMax by rememberSaveable(profile?.id) { mutableStateOf(profile?.heartRateMax?.toString().orEmpty()) }
    var hrRest by rememberSaveable(profile?.id) { mutableStateOf(profile?.heartRateRest?.toString().orEmpty()) }
    var goals by rememberSaveable(profile?.id) { mutableStateOf(profile?.trainingGoals?.joinToString(", ").orEmpty()) }
    var currentPassword by rememberSaveable { mutableStateOf("") }
    var newPassword by rememberSaveable { mutableStateOf("") }
    var confirmation by rememberSaveable { mutableStateOf("") }
    val avatarPicker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
        uri ?: return@rememberLauncherForActivityResult
        scope.launch {
            runCatching {
                withContext(Dispatchers.IO) { context.contentResolver.readAvatar(uri) }
            }.onSuccess { file -> viewModel.uploadAvatar(file.bytes, file.displayName, file.contentType) }
                .onFailure { /* Der Upload meldet Fehler über den ViewModel-Zustand. */ }
        }
    }
    LaunchedEffect(state.error, state.message) {
        (state.error ?: state.message)?.let { snackbar.showSnackbar(it); viewModel.clearNotice() }
    }
    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        topBar = { AventoTopBar("Profil", actions = { IconButton(onClick = viewModel::load) { Icon(Icons.Default.Refresh, "Aktualisieren") } }) },
    ) { padding ->
        if (state.loading && profile == null) LoadingPane("Profil wird geladen …", Modifier.padding(padding))
        else LazyColumn(
            Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            if (state.error != null && profile == null) item { ErrorPane(state.error.orEmpty(), viewModel::load) }
            profile?.let { current ->
                item {
                    Card(Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                                ProfileAvatar(current.displayName, current.avatarDataUrl, Modifier.size(72.dp))
                                Column(Modifier.weight(1f)) {
                                    Text(current.email, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                    Text("Privates Profil", style = MaterialTheme.typography.titleMedium)
                                }
                            }
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                                OutlinedButton(onClick = { avatarPicker.launch("image/*") }, modifier = Modifier.weight(1f)) { Icon(Icons.Default.Upload, null); Text("Bild", Modifier.padding(start = 6.dp)) }
                                OutlinedButton(onClick = viewModel::deleteAvatar, enabled = current.avatarDataUrl != null, modifier = Modifier.weight(1f)) { Icon(Icons.Default.Delete, null); Text("Entfernen", Modifier.padding(start = 6.dp)) }
                            }
                        }
                    }
                }
                item {
                    Card(Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            Text("Trainingsprofil", style = MaterialTheme.typography.titleLarge)
                            OutlinedTextField(displayName, { displayName = it }, label = { Text("Anzeigename") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                                OutlinedTextField(hrMax, { hrMax = it }, label = { Text("Max. Puls") }, singleLine = true, modifier = Modifier.weight(1f))
                                OutlinedTextField(hrRest, { hrRest = it }, label = { Text("Ruhepuls") }, singleLine = true, modifier = Modifier.weight(1f))
                            }
                            OutlinedTextField(goals, { goals = it }, label = { Text("Trainingsziele, durch Komma getrennt") }, minLines = 2, modifier = Modifier.fillMaxWidth())
                            Button(
                                onClick = {
                                    viewModel.save(ProfileUpdate(displayName.trim(), hrMax.toIntOrNull() ?: 0, hrRest.toIntOrNull() ?: 0, current.heartRateZones, goals.split(',').map(String::trim).filter(String::isNotBlank)))
                                },
                                enabled = !state.saving && displayName.isNotBlank() && (hrMax.toIntOrNull() ?: 0) in 80..240 && (hrRest.toIntOrNull() ?: 0) in 30..150,
                                modifier = Modifier.fillMaxWidth(),
                            ) { Text("Profil speichern") }
                        }
                    }
                }
                item {
                    Card(Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            Text("Passwort ändern", style = MaterialTheme.typography.titleLarge)
                            OutlinedTextField(currentPassword, { currentPassword = it }, label = { Text("Aktuelles Passwort") }, modifier = Modifier.fillMaxWidth())
                            OutlinedTextField(newPassword, { newPassword = it }, label = { Text("Neues Passwort") }, modifier = Modifier.fillMaxWidth())
                            OutlinedTextField(confirmation, { confirmation = it }, label = { Text("Neues Passwort wiederholen") }, modifier = Modifier.fillMaxWidth())
                            Button(onClick = { viewModel.changePassword(currentPassword, newPassword, confirmation) }, enabled = !state.saving, modifier = Modifier.fillMaxWidth()) { Icon(Icons.Default.Lock, null); Text("Passwort aktualisieren", Modifier.padding(start = 8.dp)) }
                        }
                    }
                }
            }
        }
    }
}
