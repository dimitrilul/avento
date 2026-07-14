package de.avento.app.ui.insights

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.Refresh
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import de.avento.app.ui.components.AventoTopBar
import de.avento.app.ui.components.DataBasisCard
import de.avento.app.ui.components.EmptyPane
import de.avento.app.ui.components.ErrorPane
import de.avento.app.ui.components.LoadingPane
import de.avento.app.ui.components.SectionTitle
import java.util.Locale
import de.avento.app.share.OverlayShareContent
import de.avento.app.share.ShareStudio
import de.avento.app.util.SummaryImageExporter

@Composable
fun InsightsScreen(viewModel: InsightsViewModel) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    var showShare by remember { mutableStateOf(false) }
    val insights = state.insights
    Scaffold(
        topBar = { AventoTopBar("Entwicklung", actions = { if (state.review != null && (state.reviewStatistics?.activityCount ?: 0) > 0) IconButton(onClick = { showShare = true }) { Icon(Icons.Default.Share, "Rückblick teilen") }; IconButton(onClick = viewModel::load) { Icon(Icons.Default.Refresh, "Aktualisieren") } }) },
    ) { padding ->
        LazyColumn(
            Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            item { SectionTitle("Langzeitentwicklung", "Trends und periodische Rückblicke auf Basis deiner eigenen Aktivitäten") }
            item {
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            listOf("year" to "Jahr", "spring" to "Frühling", "summer" to "Sommer", "autumn" to "Herbst", "winter" to "Winter").forEach { (value, label) ->
                                FilterChip(state.season == value, { viewModel.setSeason(value) }, label = { Text(label) })
                            }
                        }
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            OutlinedTextField(state.year.toString(), viewModel::setYear, label = { Text("Jahr") }, singleLine = true, modifier = Modifier.weight(1f))
                            Button(onClick = viewModel::load, modifier = Modifier.padding(top = 8.dp)) { Icon(Icons.Default.CalendarMonth, null); Text("Laden", Modifier.padding(start = 6.dp)) }
                        }
                    }
                }
            }
            if (state.loading && insights == null) item { LoadingPane("Entwicklung wird berechnet …") }
            else if (state.error != null && insights == null) item { ErrorPane(state.error.orEmpty(), viewModel::load) }
            else if (insights != null) {
                item { FitnessCard(insights) }
                if (insights.patterns.isNotEmpty()) {
                    item { SectionTitle("Muster in deinem Training") }
                    insights.patterns.forEach { pattern -> item(key = "pattern-${pattern.kind}") { PatternCard(pattern.kind, pattern.statement, pattern.confidence, pattern.sampleSize) } }
                }
                if (insights.monthly.isEmpty() && insights.yearly.isEmpty()) item { EmptyPane("Noch keine Entwicklung", "Importiere weitere Aktivitäten, damit Trends sichtbar werden.") }
                else {
                    item { SectionTitle("Perioden") }
                    insights.yearly.takeLast(6).forEach { aggregate -> item(key = "year-${aggregate.periodStart}") { AggregateCard(aggregate.period, aggregate.activityCount, aggregate.distanceMeters, aggregate.elevationGainMeters, aggregate.trainingLoad) } }
                }
                item { PeriodReviewCard(state.review) }
                item {
                    DataBasisCard(
                        de.avento.app.data.model.AIDataBasis(
                            methods = insights.methods,
                            limitations = listOf("Langzeitwerte sind keine medizinische Diagnose."),
                        ),
                        "Langzeit-Insights",
                    )
                }
            }
        }
    }
    if (showShare && state.review != null && state.reviewStatistics != null) {
        val review = state.review!!
        ShareStudio(
            OverlayShareContent.PeriodContent(if (review.season == "year") "Mein Radjahr ${review.year}" else "Rückblick ${review.year} · ${review.season}", "${review.period.dateFrom} – ${review.period.dateTo}", state.reviewStatistics!!, review.summary),
            emptyList(), { ByteArray(0) }, { showShare = false },
        ) { bitmap, title -> SummaryImageExporter.share(context, bitmap, title) }
    }
}

@Composable
private fun FitnessCard(insights: de.avento.app.data.model.LongTermInsights) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
            Text("Fitness-Trend: ${insights.fitnessTrend.status}", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.ExtraBold)
            Text(insights.fitnessTrend.statement)
            Text("Konfidenz: ${insights.fitnessTrend.confidence} · ${insights.fitnessTrend.sampleSize} Aktivitäten", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(insights.disclaimer, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun PatternCard(kind: String, statement: String, confidence: String, sampleSize: Int) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) { Icon(Icons.Default.AutoAwesome, null, tint = MaterialTheme.colorScheme.primary); Text(kind, fontWeight = FontWeight.Bold) }
            Text(statement)
            Text("${confidence} · $sampleSize Datenpunkte", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun AggregateCard(period: String, activities: Int, distance: Double, elevation: Double, load: Double) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(period, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Text("$activities Aktivitäten · ${String.format(Locale.GERMANY, "%.1f km", distance / 1000)} · ${elevation.toInt()} hm · Trainingslast ${load.toInt()}")
        }
    }
}

@Composable
private fun PeriodReviewCard(review: de.avento.app.data.model.PeriodReview?) {
    if (review == null) return
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Rückblick ${review.year} · ${review.season}", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.ExtraBold)
            Text(review.summary)
            Text("Erstellt mit ${review.provider}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            DataBasisCard(review.dataBasis, review.provider, "Datengrundlage")
        }
    }
}
