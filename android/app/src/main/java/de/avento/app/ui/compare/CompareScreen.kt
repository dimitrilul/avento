package de.avento.app.ui.compare

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
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.CompareArrows
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import de.avento.app.data.model.ComparisonMetric
import de.avento.app.ui.components.AventoTopBar
import de.avento.app.ui.components.DataBasisCard
import de.avento.app.ui.components.EmptyPane
import de.avento.app.ui.components.ErrorPane
import de.avento.app.ui.components.LineChart
import de.avento.app.ui.components.LoadingPane
import de.avento.app.ui.components.SectionTitle
import de.avento.app.util.asDistance
import de.avento.app.util.asDuration
import de.avento.app.util.asElevation
import de.avento.app.util.asGermanDateTime
import de.avento.app.util.asInteger
import de.avento.app.util.asSpeed
import java.util.Locale

@Composable
fun CompareScreen(viewModel: CompareViewModel, onOpenActivity: (String) -> Unit) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val result = state.result
    Scaffold(
        topBar = {
            AventoTopBar(
                title = "Vergleich",
                actions = {
                    IconButton(onClick = viewModel::loadActivities) { Icon(Icons.Default.Refresh, "Aktualisieren") }
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
                    if (result == null) "Fahrten auswählen" else "Vergleichsergebnis",
                    if (result == null) "Zwei bis zehn Aktivitäten gegenüberstellen" else "${result.activities.size} Aktivitäten im direkten Vergleich",
                )
            }
            if (state.error != null) item { ErrorPane(state.error.orEmpty()) }
            if (state.loading && state.activities.isEmpty()) {
                item { LoadingPane("Aktivitäten werden geladen …") }
            } else if (result == null) {
                item {
                    OutlinedTextField(
                        value = state.query,
                        onValueChange = viewModel::updateQuery,
                        label = { Text("Aktivität suchen") },
                        leadingIcon = { Icon(Icons.Default.Search, null) },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
                item {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        Button(
                            onClick = viewModel::compare,
                            enabled = state.selectedIds.size >= 2 && !state.comparing,
                            modifier = Modifier.weight(1f),
                        ) {
                            if (state.comparing) CircularProgressIndicator(Modifier.padding(end = 8.dp), strokeWidth = 2.dp)
                            else Icon(Icons.Default.CompareArrows, null)
                            Text("${state.selectedIds.size} vergleichen", Modifier.padding(start = 7.dp))
                        }
                        OutlinedButton(
                            onClick = viewModel::clearSelection,
                            enabled = state.selectedIds.isNotEmpty(),
                        ) { Icon(Icons.Default.Close, "Auswahl leeren") }
                    }
                }
                if (state.filteredActivities.isEmpty()) {
                    item { EmptyPane("Keine Fahrten", "Für die Suche wurden keine Aktivitäten gefunden.") }
                } else {
                    items(state.filteredActivities.take(100), key = { it.id }) { activity ->
                        val selected = activity.id in state.selectedIds
                        Card(onClick = { viewModel.toggle(activity.id) }, modifier = Modifier.fillMaxWidth()) {
                            Row(
                                Modifier.fillMaxWidth().padding(14.dp),
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                Checkbox(checked = selected, onCheckedChange = { viewModel.toggle(activity.id) })
                                Column(Modifier.weight(1f).padding(start = 8.dp)) {
                                    Text(
                                        activity.title ?: "Aktivität",
                                        fontWeight = FontWeight.Bold,
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis,
                                    )
                                    Text(
                                        "${activity.startedAt.asGermanDateTime()} · ${activity.distanceMeters.asDistance()} · ${activity.averageSpeedMps.asSpeed()}",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    )
                                }
                            }
                        }
                    }
                }
            } else {
                item {
                    OutlinedButton(onClick = { viewModel.clearSelection() }, modifier = Modifier.fillMaxWidth()) {
                        Text("Auswahl ändern")
                    }
                }
                result.aiSummary?.let { summary ->
                    item {
                        Card(Modifier.fillMaxWidth()) {
                            Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                                Text("KI-Vergleich", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.ExtraBold)
                                Text(summary, style = MaterialTheme.typography.bodyLarge)
                                result.aiProvider?.let { Text(it, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }
                            }
                        }
                    }
                }
                items(result.metrics, key = { it.activityId }) { metric ->
                    ComparisonMetricCard(metric, onClick = { onOpenActivity(metric.activityId) })
                }
                result.profiles.forEachIndexed { index, profile ->
                    item(key = "profile-${profile.activityId}") {
                        Card(Modifier.fillMaxWidth()) {
                            Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(18.dp)) {
                                Text(profile.title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                                LineChart(
                                    title = "Tempo über Streckenfortschritt",
                                    values = profile.points.map { it.speedKmh },
                                    unit = "km/h",
                                    color = comparisonColors[index % comparisonColors.size],
                                    startLabel = "Start",
                                    endLabel = "Ziel",
                                )
                                LineChart(
                                    title = "Höhenprofil",
                                    values = profile.points.map { it.elevationMeters },
                                    unit = "m",
                                    color = Color(0xFF637C16),
                                    startLabel = "Start",
                                    endLabel = "Ziel",
                                )
                            }
                        }
                    }
                }
                item {
                    DataBasisCard(result.aiDataBasis, result.aiProvider, "Datengrundlage des Vergleichs")
                }
            }
        }
    }
}

@Composable
private fun ComparisonMetricCard(metric: ComparisonMetric, onClick: () -> Unit) {
    Card(onClick = onClick, modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(11.dp)) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Text(metric.title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.ExtraBold, modifier = Modifier.weight(1f))
                metric.relativeScore?.let {
                    Surface(shape = MaterialTheme.shapes.large, color = MaterialTheme.colorScheme.primaryContainer) {
                        Text(String.format(Locale.GERMANY, "%.0f Punkte", it), Modifier.padding(horizontal = 10.dp, vertical = 5.dp), fontWeight = FontWeight.Bold)
                    }
                }
            }
            MetricLine("Distanz", metric.distanceMeters.asDistance())
            MetricLine("Bewegungszeit", metric.movingTimeSeconds.asDuration())
            MetricLine("Höhenmeter", metric.elevationGainMeters.asElevation())
            MetricLine("Ø Geschwindigkeit", metric.averageSpeedMps.asSpeed())
            MetricLine("Ø / Max. Puls", "${metric.averageHeartRate.asInteger("bpm")} / ${metric.maxHeartRate.asInteger("bpm")}")
            metric.efficiencyKmhPerBpm?.let { MetricLine("Tempoeffizienz", String.format(Locale.GERMANY, "%.3f km/h je bpm", it)) }
            metric.headwindKmh?.let { MetricLine("Streckenwind", String.format(Locale.GERMANY, "%+.1f km/h", it)) }
            metric.hydrationMilliliters?.let { MetricLine("Dokumentierte Trinkmenge", "$it ml") }
        }
    }
}

@Composable
private fun MetricLine(label: String, value: String) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, fontWeight = FontWeight.Bold)
    }
}

private val comparisonColors = listOf(Color(0xFF4D82BC), Color(0xFFE26D5A), Color(0xFF3C8B80), Color(0xFFE9A23B))
