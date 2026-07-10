package de.avento.app.ui.dashboard

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Logout
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import de.avento.app.PendingImport
import de.avento.app.data.model.Activity
import de.avento.app.data.model.OverviewStatistics
import de.avento.app.util.asDistance
import de.avento.app.util.asDuration
import de.avento.app.util.asElevation
import de.avento.app.util.asGermanDateTime
import de.avento.app.util.asSpeed

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(
    viewModel: DashboardViewModel,
    pendingImport: PendingImport?,
    onImportOffered: (PendingImport) -> Unit,
    onImportConsumed: () -> Unit,
    onOpenActivity: (String) -> Unit,
    onLoggedOut: () -> Unit,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val snackbar = remember { SnackbarHostState() }
    var query by remember { mutableStateOf("") }
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri: Uri? ->
        uri?.let {
            runCatching { context.contentResolver.takePersistableUriPermission(it, android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION) }
            onImportOffered(PendingImport(it))
        }
    }

    LaunchedEffect(state.error, state.message) {
        val notice = state.error ?: state.message
        if (notice != null) {
            snackbar.showSnackbar(notice)
            viewModel.clearNotice()
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        topBar = {
            TopAppBar(
                title = { Text("Avento", fontWeight = FontWeight.Bold) },
                actions = {
                    IconButton(onClick = { viewModel.refresh(query) }) {
                        Icon(Icons.Default.Refresh, contentDescription = "Aktualisieren")
                    }
                    IconButton(onClick = { viewModel.logout(onLoggedOut) }) {
                        Icon(Icons.AutoMirrored.Filled.Logout, contentDescription = "Abmelden")
                    }
                },
            )
        },
        floatingActionButton = {
            FloatingActionButton(
                onClick = {
                    picker.launch(
                        arrayOf(
                            "application/vnd.garmin.tcx+xml",
                            "application/xml",
                            "text/xml",
                            "application/octet-stream",
                        ),
                    )
                },
            ) { Icon(Icons.Default.Add, contentDescription = "TCX importieren") }
        },
    ) { padding ->
        LazyColumn(
            Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 96.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            item {
                Text("Übersicht", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(12.dp))
                StatisticsPanel(state.statistics)
            }
            item {
                OutlinedTextField(
                    value = query,
                    onValueChange = { query = it },
                    leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
                    label = { Text("Aktivitäten suchen") },
                    trailingIcon = {
                        TextButton(onClick = { viewModel.refresh(query) }) { Text("Suchen") }
                    },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
            if (state.loading && state.activities.isEmpty()) {
                item {
                    Row(Modifier.fillMaxWidth().padding(40.dp), horizontalArrangement = Arrangement.Center) {
                        CircularProgressIndicator()
                    }
                }
            } else if (state.activities.isEmpty()) {
                item {
                    Text(
                        "Noch keine Aktivität vorhanden. Importiere deine erste TCX-Datei.",
                        modifier = Modifier.padding(vertical = 28.dp),
                    )
                }
            } else {
                items(state.activities, key = { it.id }) { activity ->
                    ActivityCard(activity, onClick = { onOpenActivity(activity.id) })
                }
            }
        }
    }

    pendingImport?.let { import ->
        ImportDialog(
            fileName = import.displayName,
            loading = state.importing,
            onDismiss = onImportConsumed,
            onImport = { title, type, notes ->
                viewModel.upload(
                    resolver = context.contentResolver,
                    uri = import.uri,
                    fallbackName = import.displayName,
                    title = title,
                    type = type,
                    notes = notes,
                ) { activity ->
                    onImportConsumed()
                    onOpenActivity(activity.id)
                }
            },
        )
    }
}

@Composable
private fun StatisticsPanel(statistics: OverviewStatistics?) {
    Card(Modifier.fillMaxWidth()) {
        Row(
            Modifier.fillMaxWidth().padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Statistic("Aktivitäten", statistics?.activityCount?.toString() ?: "–")
            Statistic("Distanz", statistics?.distanceMeters.asDistance())
            Statistic("Höhenmeter", statistics?.elevationGainMeters.asElevation())
        }
    }
}

@Composable
private fun Statistic(label: String, value: String) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        Text(label, style = MaterialTheme.typography.labelSmall)
    }
}

@Composable
private fun ActivityCard(activity: Activity, onClick: () -> Unit) {
    Card(Modifier.fillMaxWidth().clickable(onClick = onClick)) {
        Column(Modifier.padding(16.dp)) {
            Text(
                activity.title ?: activity.originalFilename ?: "Radfahrt",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(activity.startedAt.asGermanDateTime(), style = MaterialTheme.typography.bodySmall)
            Spacer(Modifier.height(12.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(20.dp)) {
                Text(activity.distanceMeters.asDistance())
                Text(activity.movingTimeSeconds.asDuration())
                Text(activity.averageSpeedMps.asSpeed())
            }
        }
    }
}

@Composable
private fun ImportDialog(
    fileName: String?,
    loading: Boolean,
    onDismiss: () -> Unit,
    onImport: (String?, String?, String?) -> Unit,
) {
    var title by remember(fileName) { mutableStateOf(fileName?.substringBeforeLast('.').orEmpty()) }
    var type by remember { mutableStateOf("cycling") }
    var notes by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = { if (!loading) onDismiss() },
        title = { Text("TCX importieren") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                fileName?.let { Text(it, style = MaterialTheme.typography.labelMedium) }
                OutlinedTextField(title, { title = it }, label = { Text("Titel") }, singleLine = true)
                OutlinedTextField(type, { type = it }, label = { Text("Aktivitätstyp") }, singleLine = true)
                OutlinedTextField(notes, { notes = it }, label = { Text("Private Notizen") }, minLines = 2)
            }
        },
        confirmButton = {
            Button(
                onClick = { onImport(title.ifBlank { null }, type.ifBlank { null }, notes.ifBlank { null }) },
                enabled = !loading,
            ) {
                if (loading) {
                    CircularProgressIndicator(Modifier.height(20.dp).width(20.dp), strokeWidth = 2.dp)
                } else Text("Hochladen")
            }
        },
        dismissButton = { TextButton(onClick = onDismiss, enabled = !loading) { Text("Abbrechen") } },
    )
}
