package de.avento.app.ui.activities

import android.content.Intent
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.NavigateBefore
import androidx.compose.material.icons.automirrored.filled.NavigateNext
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.FilterAltOff
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import de.avento.app.ui.components.ActivityRow
import de.avento.app.ui.components.AventoTopBar
import de.avento.app.ui.components.EmptyPane
import de.avento.app.ui.components.ErrorPane
import de.avento.app.ui.components.LoadingPane
import de.avento.app.ui.components.SectionTitle
import de.avento.app.ui.components.activityTypes

@Composable
fun ActivitiesScreen(
    viewModel: ActivitiesViewModel,
    onOpenActivity: (String) -> Unit,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val snackbar = remember { SnackbarHostState() }
    var selectedImport by remember { mutableStateOf<Uri?>(null) }
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        uri?.let {
            runCatching {
                context.contentResolver.takePersistableUriPermission(it, Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            selectedImport = it
        }
    }

    LaunchedEffect(state.error, state.message) {
        (state.error ?: state.message)?.let {
            snackbar.showSnackbar(it)
            viewModel.clearNotice()
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        topBar = {
            AventoTopBar(
                title = "Aktivitäten",
                actions = {
                    IconButton(onClick = viewModel::refresh) { Icon(Icons.Default.Refresh, "Aktualisieren") }
                    IconButton(onClick = {
                        picker.launch(
                            arrayOf(
                                "application/vnd.garmin.tcx+xml",
                                "application/xml",
                                "text/xml",
                                "application/octet-stream",
                                "application/gpx+xml",
                                "application/gpx",
                            ),
                        )
                    }) { Icon(Icons.Default.Add, "Aktivität importieren") }
                },
            )
        },
    ) { padding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 18.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            item {
                SectionTitle(
                    "Dein Archiv",
                    if (state.loading && state.total == 0) "Suche und filtere deine Fahrten."
                    else "${state.total} Aktivitäten gefunden",
                )
            }
            item {
                OutlinedTextField(
                    value = state.filters.query,
                    onValueChange = viewModel::updateQuery,
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Titel oder Notizen") },
                    leadingIcon = { Icon(Icons.Default.Search, null) },
                    trailingIcon = {
                        IconButton(onClick = viewModel::applyFilters) { Icon(Icons.Default.Search, "Suchen") }
                    },
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
                    keyboardActions = KeyboardActions(onSearch = { viewModel.applyFilters() }),
                    singleLine = true,
                )
            }
            item {
                Row(
                    Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    FilterChip(
                        selected = state.filters.type.isBlank(),
                        onClick = { viewModel.updateType("") },
                        label = { Text("Alle") },
                    )
                    activityTypes.forEach { (value, label) ->
                        FilterChip(
                            selected = state.filters.type == value,
                            onClick = { viewModel.updateType(value) },
                            label = { Text(label) },
                        )
                    }
                }
            }
            item {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedTextField(
                        value = state.filters.dateFrom,
                        onValueChange = viewModel::updateDateFrom,
                        label = { Text("Von") },
                        placeholder = { Text("JJJJ-MM-TT") },
                        singleLine = true,
                        modifier = Modifier.weight(1f),
                    )
                    OutlinedTextField(
                        value = state.filters.dateTo,
                        onValueChange = viewModel::updateDateTo,
                        label = { Text("Bis") },
                        placeholder = { Text("JJJJ-MM-TT") },
                        singleLine = true,
                        modifier = Modifier.weight(1f),
                    )
                }
            }
            item {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Button(onClick = viewModel::applyFilters, modifier = Modifier.weight(1f)) {
                        Icon(Icons.Default.Search, null)
                        Text("Anwenden", Modifier.padding(start = 7.dp))
                    }
                    OutlinedButton(onClick = viewModel::resetFilters, modifier = Modifier.weight(1f)) {
                        Icon(Icons.Default.FilterAltOff, null)
                        Text("Zurücksetzen", Modifier.padding(start = 7.dp))
                    }
                }
            }
            if (state.loading && state.activities.isEmpty()) {
                item { LoadingPane() }
            } else if (state.activities.isEmpty()) {
                item {
                    if (state.error != null) ErrorPane(state.error.orEmpty(), viewModel::refresh)
                    else EmptyPane("Keine Aktivitäten", "Passe die Filter an oder importiere eine TCX-Datei.")
                }
            } else {
                items(state.activities, key = { it.id }) { activity ->
                    ActivityRow(activity, onClick = { onOpenActivity(activity.id) })
                }
                item {
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                    ) {
                        OutlinedButton(onClick = viewModel::previousPage, enabled = state.canGoBack && !state.loading) {
                            Icon(Icons.AutoMirrored.Filled.NavigateBefore, null)
                            Text("Zurück")
                        }
                        Text(
                            "Seite ${state.page} von ${state.pageCount}",
                            modifier = Modifier.padding(top = 12.dp),
                            style = MaterialTheme.typography.labelLarge,
                        )
                        OutlinedButton(onClick = viewModel::nextPage, enabled = state.canGoForward && !state.loading) {
                            Text("Weiter")
                            Icon(Icons.AutoMirrored.Filled.NavigateNext, null)
                        }
                    }
                }
            }
        }
    }

    selectedImport?.let { uri ->
        ActivityImportDialog(
            loading = state.importing,
            onDismiss = { if (!state.importing) selectedImport = null },
            onImport = { title, type, notes, hydration ->
                viewModel.upload(
                    resolver = context.contentResolver,
                    uri = uri,
                    title = title,
                    type = type,
                    notes = notes,
                    hydration = hydration,
                ) { activity ->
                    selectedImport = null
                    onOpenActivity(activity.id)
                }
            },
        )
    }
}

@Composable
private fun ActivityImportDialog(
    loading: Boolean,
    onDismiss: () -> Unit,
    onImport: (String?, String?, String?, String?) -> Unit,
) {
    var title by rememberSaveable { mutableStateOf("") }
    var type by rememberSaveable { mutableStateOf("ride") }
    var notes by rememberSaveable { mutableStateOf("") }
    var hydration by rememberSaveable { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("TCX importieren") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedTextField(title, { title = it }, label = { Text("Titel (optional)") }, singleLine = true)
                Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                    activityTypes.forEach { (value, label) ->
                        FilterChip(selected = type == value, onClick = { type = value }, label = { Text(label) })
                    }
                }
                OutlinedTextField(
                    hydration,
                    { hydration = it.filter(Char::isDigit) },
                    label = { Text("Trinkmenge in ml (optional)") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    singleLine = true,
                )
                OutlinedTextField(notes, { notes = it }, label = { Text("Notizen (optional)") }, minLines = 2)
            }
        },
        confirmButton = {
            Button(
                onClick = { onImport(title.ifBlank { null }, type, notes.ifBlank { null }, hydration.ifBlank { null }) },
                enabled = !loading,
            ) {
                if (loading) CircularProgressIndicator(Modifier.padding(end = 8.dp), strokeWidth = 2.dp)
                Text(if (loading) "Wird importiert …" else "Importieren")
            }
        },
        dismissButton = { TextButton(onClick = onDismiss, enabled = !loading) { Text("Abbrechen") } },
    )
}
