package de.avento.app.ui.statistics

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccessTime
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Landscape
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Route
import androidx.compose.material.icons.filled.Speed
import androidx.compose.material.icons.filled.WaterDrop
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import de.avento.app.ui.components.AventoTopBar
import de.avento.app.ui.components.EmptyPane
import de.avento.app.ui.components.ErrorPane
import de.avento.app.ui.components.LineChart
import de.avento.app.ui.components.LoadingPane
import de.avento.app.ui.components.MetricTile
import de.avento.app.ui.components.SectionTitle
import de.avento.app.util.asDistance
import de.avento.app.util.asDuration
import de.avento.app.util.asElevation
import de.avento.app.util.asInteger
import de.avento.app.util.asSpeed
import de.avento.app.share.OverlayShareContent
import de.avento.app.share.ShareStudio
import de.avento.app.util.SummaryImageExporter
import java.util.Locale

@Composable
fun StatisticsScreen(viewModel: StatisticsViewModel) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    var showShare by remember { mutableStateOf(false) }
    val data = state.statistics
    Scaffold(
        topBar = {
            AventoTopBar(
                title = "Statistiken",
                actions = {
                    if (data != null && data.activityCount > 0) IconButton(onClick = { showShare = true }) { Icon(Icons.Default.Share, "Rückblick teilen") }
                    IconButton(onClick = viewModel::load) { Icon(Icons.Default.Refresh, "Aktualisieren") }
                },
            )
        },
    ) { padding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 18.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            item { SectionTitle("Dein Training in Zahlen", "Zeiträume vergleichen und Trends erkennen") }
            item {
                Row(
                    Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    listOf("last_week" to "Letzte Woche", "last_month" to "Letzter Monat", "30" to "30 Tage", "90" to "90 Tage", "year" to "Dieses Jahr", "all" to "Gesamt").forEach { (value, label) ->
                        FilterChip(selected = state.preset == value, onClick = { viewModel.setPreset(value) }, label = { Text(label) })
                    }
                }
            }
            item {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedTextField(
                        value = state.dateFrom,
                        onValueChange = viewModel::updateDateFrom,
                        label = { Text("Von") },
                        placeholder = { Text("JJJJ-MM-TT") },
                        singleLine = true,
                        modifier = Modifier.weight(1f),
                    )
                    OutlinedTextField(
                        value = state.dateTo,
                        onValueChange = viewModel::updateDateTo,
                        label = { Text("Bis") },
                        placeholder = { Text("JJJJ-MM-TT") },
                        singleLine = true,
                        modifier = Modifier.weight(1f),
                    )
                }
            }
            item {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Row(
                        Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        listOf("auto" to "Automatisch", "day" to "Täglich", "week" to "Wöchentlich", "month" to "Monatlich").forEach { (value, label) ->
                            FilterChip(selected = state.granularity == value, onClick = { viewModel.setGranularity(value) }, label = { Text(label) })
                        }
                    }
                    Button(onClick = viewModel::load, modifier = Modifier.fillMaxWidth()) { Text("Zeitraum anwenden") }
                }
            }
            if (state.loading && data == null) {
                item { LoadingPane("Statistiken werden berechnet …") }
            } else if (state.error != null && data == null) {
                item { ErrorPane(state.error.orEmpty(), viewModel::load) }
            } else if (data != null) {
                if (data.activityCount == 0) {
                    item { EmptyPane("Keine Daten", "In diesem Zeitraum wurden keine Aktivitäten gefunden.") }
                } else {
                    item {
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            MetricTile("Aktivitäten", data.activityCount.toString(), Icons.Default.Route, Modifier.weight(1f))
                            MetricTile("Distanz", data.distanceMeters.asDistance(), Icons.Default.Route, Modifier.weight(1f))
                        }
                    }
                    item {
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            MetricTile("Bewegungszeit", data.movingTimeSeconds.asDuration(), Icons.Default.AccessTime, Modifier.weight(1f))
                            MetricTile("Höhenmeter", data.elevationGainMeters.asElevation(), Icons.Default.Landscape, Modifier.weight(1f))
                        }
                    }
                    item {
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            MetricTile("Ø Tempo", data.averageSpeedMps.asSpeed(), Icons.Default.Speed, Modifier.weight(1f))
                            MetricTile("Ø Puls", data.averageHeartRate.asInteger("bpm"), Icons.Default.Favorite, Modifier.weight(1f))
                        }
                    }
                    item {
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            MetricTile("Trainingslast", String.format(Locale.GERMANY, "%.0f", data.trainingLoad), Icons.Default.Speed, Modifier.weight(1f))
                            MetricTile("Trinkmenge", "${data.hydrationMilliliters} ml", Icons.Default.WaterDrop, Modifier.weight(1f), "${data.hydrationActivityCount} erfasste Fahrten")
                        }
                    }
                    if (data.series.isNotEmpty()) {
                        item {
                            StatisticsChartCard {
                                LineChart(
                                    title = "Distanzverlauf",
                                    values = data.series.map { it.distanceMeters / 1000.0 },
                                    unit = "km",
                                    color = Color(0xFF4D82BC),
                                    startLabel = data.series.first().periodStart,
                                    endLabel = data.series.last().periodStart,
                                )
                            }
                        }
                        item {
                            StatisticsChartCard {
                                LineChart(
                                    title = "Geschwindigkeit",
                                    values = data.series.map { it.averageSpeedMps?.times(3.6) },
                                    unit = "km/h",
                                    color = Color(0xFF3C8B80),
                                    startLabel = data.series.first().periodStart,
                                    endLabel = data.series.last().periodStart,
                                )
                            }
                        }
                        item {
                            StatisticsChartCard {
                                LineChart(
                                    title = "Trainingslast",
                                    values = data.series.map { it.trainingLoad },
                                    unit = "Punkte",
                                    color = Color(0xFFE9A23B),
                                    startLabel = data.series.first().periodStart,
                                    endLabel = data.series.last().periodStart,
                                )
                            }
                        }
                    }
                    data.comparison?.let { comparison ->
                        item {
                            Card(Modifier.fillMaxWidth()) {
                                Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                                    SectionTitle("Gegen Vorperiode", "${comparison.dateFrom} bis ${comparison.dateTo}")
                                    comparison.changes.entries.take(10).forEach { (key, value) ->
                                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                            Text(key.metricLabel(), color = MaterialTheme.colorScheme.onSurfaceVariant)
                                            Text(
                                                value?.let { String.format(Locale.GERMANY, "%+.1f %%", it) } ?: "–",
                                                fontWeight = FontWeight.Bold,
                                                color = when {
                                                    value == null -> MaterialTheme.colorScheme.onSurfaceVariant
                                                    value >= 0 -> MaterialTheme.colorScheme.primary
                                                    else -> MaterialTheme.colorScheme.error
                                                },
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            if (state.error != null && data != null) item { ErrorPane(state.error.orEmpty(), viewModel::load) }
        }
    }
    if (showShare && data != null) {
        val title = when (state.preset) { "last_week" -> "Meine Woche auf dem Rad"; "last_month" -> "Mein Monatsrückblick"; "year" -> "Mein Radjahr ${java.time.LocalDate.now().year}"; else -> "Mein Radrückblick" }
        ShareStudio(
            content = OverlayShareContent.PeriodContent(title, "${state.dateFrom} – ${state.dateTo}", data),
            photos = emptyList(),
            loadPhoto = { ByteArray(0) },
            onDismiss = { showShare = false },
            onShare = { bitmap, name -> SummaryImageExporter.share(context, bitmap, name) },
        )
    }
}

@Composable
private fun StatisticsChartCard(content: @Composable () -> Unit) {
    Card(Modifier.fillMaxWidth()) { Column(Modifier.padding(18.dp)) { content() } }
}

private fun String.metricLabel(): String = when (this) {
    "activity_count" -> "Aktivitäten"
    "distance_m" -> "Distanz"
    "duration_s" -> "Gesamtzeit"
    "moving_time_s" -> "Bewegungszeit"
    "elevation_gain_m" -> "Höhenmeter"
    "training_load" -> "Trainingslast"
    "avg_speed_mps" -> "Ø Geschwindigkeit"
    "avg_hr_bpm" -> "Ø Herzfrequenz"
    "hydration_ml" -> "Trinkmenge"
    else -> replace('_', ' ').replaceFirstChar(Char::uppercase)
}
