package de.avento.app.ui.records

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.EmojiEvents
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Card
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import de.avento.app.data.model.ActivityRecord
import de.avento.app.data.model.DistanceRecord
import de.avento.app.ui.components.AventoTopBar
import de.avento.app.ui.components.EmptyPane
import de.avento.app.ui.components.ErrorPane
import de.avento.app.ui.components.LoadingPane
import de.avento.app.ui.components.SectionTitle
import de.avento.app.util.asDistance
import de.avento.app.util.asDuration
import de.avento.app.util.asGermanDateTime
import de.avento.app.util.asSpeed

@Composable
fun RecordsScreen(
    viewModel: RecordsViewModel,
    onBack: () -> Unit,
    onOpenActivity: (String) -> Unit,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val records = state.records
    Scaffold(
        topBar = {
            AventoTopBar("Persönliche Rekorde", onBack) {
                IconButton(onClick = viewModel::load) { Icon(Icons.Default.Refresh, "Aktualisieren") }
            }
        },
    ) { padding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 18.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            item { SectionTitle("Deine Bestleistungen", "Schnellste Abschnitte und herausragende Fahrten") }
            if (state.loading && records == null) item { LoadingPane("Rekorde werden berechnet …") }
            if (state.error != null && records == null) item { ErrorPane(state.error.orEmpty(), viewModel::load) }
            if (records != null) {
                if (records.distanceRecords.isEmpty() && records.longestRide == null) {
                    item { EmptyPane("Noch keine Rekorde", "Importiere Aktivitäten mit Trackpunkten, um Bestzeiten zu ermitteln.") }
                } else {
                    records.longestRide?.let { record ->
                        item { HighlightRecord("Längste Fahrt", record, onOpenActivity) }
                    }
                    records.highestAverageSpeed?.let { record ->
                        item { HighlightRecord("Höchstes Durchschnittstempo", record, onOpenActivity) }
                    }
                    if (records.distanceRecords.isNotEmpty()) item { SectionTitle("Distanzrekorde", "Schnellster zusammenhängender Abschnitt je Distanz") }
                    items(records.distanceRecords, key = { it.targetDistanceMeters }) { record ->
                        DistanceRecordCard(record, onOpenActivity)
                    }
                    if (records.methods.isNotEmpty()) {
                        item {
                            Card(Modifier.fillMaxWidth()) {
                                Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                    Text("Berechnung", fontWeight = FontWeight.ExtraBold)
                                    records.methods.forEach { method ->
                                        Text("• ${method.description}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun HighlightRecord(label: String, record: ActivityRecord, onOpenActivity: (String) -> Unit) {
    Card(onClick = { onOpenActivity(record.activityId) }, modifier = Modifier.fillMaxWidth()) {
        Row(Modifier.padding(18.dp), verticalAlignment = Alignment.CenterVertically) {
            Surface(shape = MaterialTheme.shapes.large, color = MaterialTheme.colorScheme.primaryContainer) {
                Icon(Icons.Default.EmojiEvents, null, Modifier.padding(12.dp), tint = MaterialTheme.colorScheme.onPrimaryContainer)
            }
            Column(Modifier.weight(1f).padding(start = 14.dp)) {
                Text(label, color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.labelLarge)
                Text(record.title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.ExtraBold)
                Text(
                    "${record.distanceMeters.asDistance()} · ${record.movingTimeSeconds.asDuration()} · ${record.averageSpeedMps.asSpeed()}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

@Composable
private fun DistanceRecordCard(record: DistanceRecord, onOpenActivity: (String) -> Unit) {
    Card(onClick = { onOpenActivity(record.activityId) }, modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Text(record.targetDistanceMeters.toDouble().asDistance(), style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.ExtraBold)
                Surface(shape = MaterialTheme.shapes.large, color = MaterialTheme.colorScheme.secondaryContainer) {
                    Text(record.durationSeconds.asDuration(), Modifier.padding(horizontal = 10.dp, vertical = 5.dp), fontWeight = FontWeight.Bold)
                }
            }
            Text(record.title, fontWeight = FontWeight.Bold)
            Text("${record.averageSpeedMps.asSpeed()} · ${record.startedAt.asGermanDateTime()}", color = MaterialTheme.colorScheme.onSurfaceVariant)
            if (record.estimated) Text("Aus dem Aktivitätsdurchschnitt geschätzt", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.error)
        }
    }
}
