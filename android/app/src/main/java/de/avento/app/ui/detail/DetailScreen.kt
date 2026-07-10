package de.avento.app.ui.detail

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
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
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import de.avento.app.data.model.Activity
import de.avento.app.data.model.TrackPoint
import de.avento.app.data.model.WeatherResponse
import de.avento.app.ui.components.LineChart
import de.avento.app.ui.components.RoutePreview
import de.avento.app.util.SummaryImageExporter
import de.avento.app.util.asDistance
import de.avento.app.util.asDuration
import de.avento.app.util.asElevation
import de.avento.app.util.asGermanDateTime
import de.avento.app.util.asInteger
import de.avento.app.util.asSpeed

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DetailScreen(viewModel: DetailViewModel, onBack: () -> Unit, onDeleted: () -> Unit) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val snackbar = remember { SnackbarHostState() }
    var showEdit by remember { mutableStateOf(false) }
    var showDelete by remember { mutableStateOf(false) }

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
                title = { Text(state.activity?.title ?: "Aktivität") },
                navigationIcon = {
                    IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Zurück") }
                },
                actions = {
                    state.activity?.let { activity ->
                        IconButton(onClick = { SummaryImageExporter.share(context, activity, state.track) }) {
                            Icon(Icons.Default.Share, "Als Bild teilen")
                        }
                        IconButton(onClick = { showEdit = true }) { Icon(Icons.Default.Edit, "Bearbeiten") }
                        IconButton(onClick = { showDelete = true }) { Icon(Icons.Default.Delete, "Löschen") }
                    }
                },
            )
        },
    ) { padding ->
        when {
            state.loading && state.activity == null -> Column(
                Modifier.fillMaxSize().padding(padding),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center,
            ) { CircularProgressIndicator() }
            state.activity != null -> ActivityContent(
                activity = state.activity!!,
                points = state.track?.points.orEmpty(),
                weather = state.weather,
                summary = state.summary?.summary ?: state.activity?.aiSummary,
                refreshingWeather = state.refreshingWeather,
                generatingSummary = state.generatingSummary,
                onRefreshWeather = viewModel::refreshWeather,
                onGenerateSummary = { viewModel.generateSummary(state.summary != null) },
                contentPadding = padding,
            )
            else -> Column(Modifier.padding(padding).padding(24.dp)) {
                Text(state.error ?: "Aktivität konnte nicht geladen werden.")
                Button(onClick = viewModel::load) { Text("Erneut versuchen") }
            }
        }
    }

    if (showEdit) state.activity?.let { activity ->
        EditDialog(activity, state.saving, { showEdit = false }) { title, type, notes ->
            viewModel.save(title, type, notes) { showEdit = false }
        }
    }
    if (showDelete) AlertDialog(
        onDismissRequest = { if (!state.saving) showDelete = false },
        title = { Text("Aktivität löschen?") },
        text = { Text("Die Aktivität und ihre TCX-Datei werden dauerhaft vom Server entfernt.") },
        confirmButton = {
            Button(onClick = { viewModel.delete(onDeleted) }, enabled = !state.saving) { Text("Löschen") }
        },
        dismissButton = { TextButton(onClick = { showDelete = false }) { Text("Abbrechen") } },
    )
}

@Composable
private fun ActivityContent(
    activity: Activity,
    points: List<TrackPoint>,
    weather: WeatherResponse?,
    summary: String?,
    refreshingWeather: Boolean,
    generatingSummary: Boolean,
    onRefreshWeather: () -> Unit,
    onGenerateSummary: () -> Unit,
    contentPadding: PaddingValues,
) {
    LazyColumn(
        Modifier.fillMaxSize().padding(contentPadding),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item {
            Text(activity.startedAt.asGermanDateTime(), style = MaterialTheme.typography.bodyMedium)
            Spacer(Modifier.height(12.dp))
            MetricGrid(activity)
        }
        if (points.any { it.latitude != null && it.longitude != null }) {
            item { Card { Column { RoutePreview(points); Text("Streckenverlauf", Modifier.padding(12.dp)) } } }
        }
        item {
            WeatherCard(weather, activity.weather, refreshingWeather, onRefreshWeather)
        }
        item {
            AiCard(summary, activity.aiProvider, generatingSummary, onGenerateSummary)
        }
        if (points.any { it.altitudeMeters != null }) {
            item { ChartCard { LineChart("Höhenprofil", points.map { it.altitudeMeters }, "m") } }
        }
        if (points.any { it.heartRate != null }) {
            item { ChartCard { LineChart("Herzfrequenz", points.map { it.heartRate }, "bpm") } }
        }
        if (points.any { it.speedMps != null }) {
            item { ChartCard { LineChart("Geschwindigkeit", points.map { it.speedMps?.times(3.6) }, "km/h") } }
        }
        activity.notes?.takeIf { it.isNotBlank() }?.let { notes ->
            item { Card { Column(Modifier.padding(16.dp)) { Text("Notizen", fontWeight = FontWeight.Bold); Text(notes) } } }
        }
    }
}

@Composable
private fun MetricGrid(activity: Activity) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            MetricRow("Distanz", activity.distanceMeters.asDistance(), "Bewegungszeit", activity.movingTimeSeconds.asDuration())
            MetricRow("Ø Geschwindigkeit", activity.averageSpeedMps.asSpeed(), "Höhenmeter", activity.elevationGainMeters.asElevation())
            MetricRow("Ø Herzfrequenz", activity.averageHeartRate.asInteger("bpm"), "Max. Herzfrequenz", activity.maxHeartRate.asInteger("bpm"))
            MetricRow("Max. Tempo", activity.maxSpeedMps.asSpeed(), "Gesamtzeit", activity.durationSeconds.asDuration())
        }
    }
}

@Composable
private fun MetricRow(label1: String, value1: String, label2: String, value2: String) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
        Metric(label1, value1, Modifier.weight(1f)); Metric(label2, value2, Modifier.weight(1f))
    }
}

@Composable
private fun Metric(label: String, value: String, modifier: Modifier) {
    Column(modifier) { Text(label, style = MaterialTheme.typography.labelMedium); Text(value, style = MaterialTheme.typography.titleLarge) }
}

@Composable
private fun WeatherCard(
    weather: WeatherResponse?,
    embedded: Map<String, Any?>?,
    loading: Boolean,
    onRefresh: () -> Unit,
) {
    val data = weather?.data ?: embedded
    val temperature = data.value("temperature_c", "temperature", "temp_c")?.let { "$it °C" }
    val description = data.value("description", "condition", "weather_code")
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Text("Wetter", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                IconButton(onClick = onRefresh, enabled = !loading) {
                    if (loading) CircularProgressIndicator(Modifier.height(22.dp), strokeWidth = 2.dp)
                    else Icon(Icons.Default.Refresh, "Wetter aktualisieren")
                }
            }
            Text(listOfNotNull(temperature, description).joinToString(" · ").ifBlank { "Noch keine Wetterdaten vorhanden." })
            data.value("wind_speed_kmh")?.let { Text("Wind: $it km/h") }
        }
    }
}

private fun Map<String, Any?>?.value(vararg keys: String): String? = keys.firstNotNullOfOrNull { key ->
    this?.get(key)?.toString()?.takeIf { it.isNotBlank() }
}

@Composable
private fun AiCard(summary: String?, provider: String?, loading: Boolean, onGenerate: () -> Unit) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("KI-Auswertung", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Text(summary ?: "Lass Avento diese Fahrt zusammenfassen und einordnen.")
            provider?.let { Text("Erstellt mit $it", style = MaterialTheme.typography.labelSmall) }
            OutlinedButton(onClick = onGenerate, enabled = !loading) {
                if (loading) CircularProgressIndicator(Modifier.height(20.dp), strokeWidth = 2.dp)
                else Text(if (summary == null) "Auswertung erstellen" else "Neu erstellen")
            }
        }
    }
}

@Composable
private fun ChartCard(content: @Composable () -> Unit) = Card(Modifier.fillMaxWidth()) {
    Column(Modifier.padding(16.dp)) { content() }
}

@Composable
private fun EditDialog(activity: Activity, saving: Boolean, onDismiss: () -> Unit, onSave: (String?, String?, String?) -> Unit) {
    var title by remember { mutableStateOf(activity.title.orEmpty()) }
    var type by remember { mutableStateOf(activity.type.orEmpty()) }
    var notes by remember { mutableStateOf(activity.notes.orEmpty()) }
    AlertDialog(
        onDismissRequest = { if (!saving) onDismiss() },
        title = { Text("Aktivität bearbeiten") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedTextField(title, { title = it }, label = { Text("Titel") })
                OutlinedTextField(type, { type = it }, label = { Text("Typ") })
                OutlinedTextField(notes, { notes = it }, label = { Text("Notizen") }, minLines = 3)
            }
        },
        confirmButton = { Button(onClick = { onSave(title.ifBlank { null }, type.ifBlank { null }, notes.ifBlank { null }) }, enabled = !saving) { Text("Speichern") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Abbrechen") } },
    )
}
