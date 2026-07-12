package de.avento.app.ui.health

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.DirectionsRun
import androidx.compose.material.icons.filled.Bedtime
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Cloud
import androidx.compose.material.icons.filled.DeleteOutline
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.MonitorHeart
import androidx.compose.material.icons.filled.OpenInBrowser
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import de.avento.app.data.model.HealthConnectionStatus
import de.avento.app.data.model.HealthData
import de.avento.app.data.model.HealthExercise
import de.avento.app.data.model.HealthMetric
import de.avento.app.data.model.HealthOverview
import de.avento.app.data.model.HealthScore
import de.avento.app.data.model.HealthSleepSession
import de.avento.app.ui.components.EmptyPane
import de.avento.app.ui.components.ErrorPane
import de.avento.app.util.asDistance
import de.avento.app.util.asDuration
import de.avento.app.util.asGermanDateTime
import java.text.DecimalFormat
import java.text.DecimalFormatSymbols
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HealthScreen(
    viewModel: HealthViewModel,
    onBack: () -> Unit,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val uriHandler = LocalUriHandler.current
    val snackbar = remember { SnackbarHostState() }
    var confirmDisconnect by remember { mutableStateOf(false) }

    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) {
        viewModel.onForeground()
    }
    LaunchedEffect(state.oauthLaunch) {
        val launch = state.oauthLaunch ?: return@LaunchedEffect
        viewModel.consumeOAuthLaunch()
        runCatching { uriHandler.openUri(launch.authorizationUrl) }
            .onFailure { viewModel.oauthLaunchFailed() }
    }
    LaunchedEffect(state.actionError, state.message) {
        val notice = state.actionError ?: state.message
        if (notice != null) {
            snackbar.showSnackbar(notice)
            viewModel.clearNotice()
        }
    }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        snackbarHost = { SnackbarHost(snackbar) },
        topBar = {
            TopAppBar(
                title = { Text("Gesundheit") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, "Zurück")
                    }
                },
                actions = {
                    IconButton(
                        onClick = viewModel::refresh,
                        enabled = !state.refreshing && !state.initialLoading,
                    ) {
                        Icon(Icons.Default.Refresh, "Status aktualisieren")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.background,
                    scrolledContainerColor = MaterialTheme.colorScheme.surface,
                ),
            )
        },
    ) { padding ->
        when {
            state.initialLoading -> Box(
                Modifier.fillMaxSize().padding(padding),
                contentAlignment = Alignment.Center,
            ) { CircularProgressIndicator() }

            state.connectionError != null -> Box(
                Modifier.fillMaxSize().padding(padding).padding(20.dp),
                contentAlignment = Alignment.Center,
            ) {
                ErrorPane(state.connectionError.orEmpty(), viewModel::refresh)
            }

            else -> HealthContent(
                state = state,
                onConnect = viewModel::startOAuth,
                onSync = { viewModel.synchronize() },
                onRetry = viewModel::refresh,
                onDisconnect = { confirmDisconnect = true },
                modifier = Modifier.padding(padding),
            )
        }
    }

    if (confirmDisconnect) {
        AlertDialog(
            onDismissRequest = { confirmDisconnect = false },
            title = { Text("Google Health trennen?") },
            text = {
                Text(
                    "Die Verbindung wird widerrufen. Importierte Google-Health-Daten, Aggregate und Scores werden aus Avento gelöscht.",
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        confirmDisconnect = false
                        viewModel.disconnect()
                    },
                ) { Text("Trennen und löschen") }
            },
            dismissButton = {
                TextButton(onClick = { confirmDisconnect = false }) { Text("Abbrechen") }
            },
        )
    }
}

@Composable
private fun HealthContent(
    state: HealthUiState,
    onConnect: () -> Unit,
    onSync: () -> Unit,
    onRetry: () -> Unit,
    onDisconnect: () -> Unit,
    modifier: Modifier = Modifier,
) {
    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 18.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        item {
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("Tagesform & Erholung", style = MaterialTheme.typography.headlineSmall)
                Text(
                    "Cloudbasierte Fitness- und Wellness-Einschätzungen aus Google Health.",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
        item { WellnessNotice() }

        if (!state.connected) {
            item {
                DisconnectedCard(
                    connection = state.connection,
                    loading = state.connecting,
                    disconnecting = state.disconnecting,
                    onConnect = onConnect,
                    onDisconnect = onDisconnect,
                )
            }
        } else {
            item {
                ConnectionCard(
                    connection = requireNotNull(state.connection),
                    syncing = state.syncing,
                    connecting = state.connecting,
                    disconnecting = state.disconnecting,
                    onSync = onSync,
                    onReconnect = onConnect,
                    onDisconnect = onDisconnect,
                )
            }
            if (state.hasPartialData) {
                item { PartialDataNotice(onRetry) }
            }
            if (state.isEmpty && !state.hasPartialData) {
                item {
                    EmptyPane(
                        "Noch keine Gesundheitsdaten",
                        "Starte eine manuelle Synchronisation. Je nach Google-Freigabe können einzelne Bereiche leer bleiben.",
                    )
                }
            }

            item { SectionTitle("Scores", Icons.Default.Favorite) }
            when {
                state.scoresError != null -> item { ErrorPane(state.scoresError, onRetry) }
                state.overview != null -> item { ScoreSection(requireNotNull(state.overview)) }
            }

            item { SectionTitle("Aktuelle Daten", Icons.Default.MonitorHeart) }
            when {
                state.dataError != null -> item { ErrorPane(state.dataError, onRetry) }
                state.data != null -> item { HealthDataSection(requireNotNull(state.data)) }
            }
        }
    }
}

@Composable
private fun WellnessNotice() {
    Surface(
        shape = MaterialTheme.shapes.medium,
        color = MaterialTheme.colorScheme.tertiaryContainer.copy(alpha = 0.65f),
    ) {
        Row(
            Modifier.fillMaxWidth().padding(14.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.Top,
        ) {
            Icon(Icons.Default.Info, null, tint = MaterialTheme.colorScheme.onTertiaryContainer)
            Text(
                "Avento zeigt Wellness- und Fitnesswerte, keine medizinische Diagnose. Bei Beschwerden wende dich an medizinisches Fachpersonal.",
                color = MaterialTheme.colorScheme.onTertiaryContainer,
                style = MaterialTheme.typography.bodySmall,
            )
        }
    }
}

@Composable
private fun DisconnectedCard(
    connection: HealthConnectionStatus?,
    loading: Boolean,
    disconnecting: Boolean,
    onConnect: () -> Unit,
    onDisconnect: () -> Unit,
) {
    val status = connection?.status.orEmpty()
    val enabled = connection?.enabled != false
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Icon(Icons.Default.Cloud, null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(32.dp))
            Text("Google Health verbinden", style = MaterialTheme.typography.titleLarge)
            Text(
                if (!enabled) {
                    "Google Health ist auf diesem Avento-Server noch nicht aktiviert. Prüfe zuerst die Serverkonfiguration."
                } else if (status == "reauthorization_required") {
                    "Die bisherige Freigabe ist abgelaufen oder unvollständig. Verbinde dein Google-Konto erneut."
                } else {
                    "Die Anmeldung erfolgt im Browser. Avento Android erhält und speichert dabei keine Google-Tokens."
                },
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Button(onClick = onConnect, enabled = enabled && !loading) {
                if (loading) CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
                else Icon(Icons.Default.OpenInBrowser, null)
                Spacer(Modifier.width(8.dp))
                Text(if (status == "reauthorization_required") "Erneut verbinden" else "Mit Google verbinden")
            }
            if (status !in setOf("", "disconnected")) {
                TextButton(onClick = onDisconnect, enabled = !disconnecting) {
                    Text("Vorhandene Verbindung entfernen")
                }
            }
        }
    }
}

@Composable
private fun ConnectionCard(
    connection: HealthConnectionStatus,
    syncing: Boolean,
    connecting: Boolean,
    disconnecting: Boolean,
    onSync: () -> Unit,
    onReconnect: () -> Unit,
    onDisconnect: () -> Unit,
) {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(13.dp)) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.CheckCircle, null, tint = MaterialTheme.colorScheme.primary)
                Spacer(Modifier.width(10.dp))
                Column(Modifier.weight(1f)) {
                    Text("Google Health API", style = MaterialTheme.typography.titleMedium)
                    Text(
                        if (connection.mockMode) "Verbunden · lokaler Testmodus" else "Verbunden · Cloud",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                StatusLabel(connection.status)
            }
            HorizontalDivider()
            DetailLine(
                "Letzte Synchronisation",
                connection.lastSyncAt?.asGermanDateTime() ?: "Noch nicht synchronisiert",
            )
            connection.lastErrorCode?.let { DetailLine("Letzter Statushinweis", healthErrorLabel(it)) }

            Text("Freigegebene Bereiche", style = MaterialTheme.typography.labelLarge)
            if (connection.grantedScopes.isEmpty()) {
                Text("Keine bestätigten Lesebereiche", color = MaterialTheme.colorScheme.error)
            } else {
                connection.grantedScopes.forEach { scope ->
                    Text("• ${healthScopeLabel(scope)}", style = MaterialTheme.typography.bodySmall)
                }
            }
            if (connection.missingScopes.isNotEmpty()) {
                Surface(
                    shape = MaterialTheme.shapes.small,
                    color = MaterialTheme.colorScheme.errorContainer,
                ) {
                    Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text("Freigabe unvollständig", fontWeight = FontWeight.Bold)
                        connection.missingScopes.forEach { Text("• ${healthScopeLabel(it)}", style = MaterialTheme.typography.bodySmall) }
                        OutlinedButton(onClick = onReconnect, enabled = !connecting) {
                            Icon(Icons.Default.Link, null)
                            Spacer(Modifier.width(8.dp))
                            Text("Freigabe ergänzen")
                        }
                    }
                }
            }

            Text("Datenquellen", style = MaterialTheme.typography.labelLarge)
            if (connection.sources.isEmpty()) {
                Text(
                    "Google Health API · Geräte- und App-Quellen erscheinen nach einer Synchronisation, sobald der Server sie meldet.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            } else {
                connection.sources.forEach { source ->
                    val title = source.deviceName ?: source.applicationName ?: source.platform ?: "Google-Health-Quelle"
                    val detail = listOfNotNull(source.deviceManufacturer, source.recordingMethod, source.platform)
                        .distinct().joinToString(" · ")
                    Column {
                        Text(title, fontWeight = FontWeight.SemiBold)
                        if (detail.isNotBlank()) Text(detail, style = MaterialTheme.typography.bodySmall)
                    }
                }
            }

            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Button(
                    onClick = onSync,
                    enabled = !syncing && connection.missingScopes.isEmpty(),
                    modifier = Modifier.weight(1f),
                ) {
                    if (syncing) CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
                    else Icon(Icons.Default.Sync, null)
                    Spacer(Modifier.width(7.dp))
                    Text(if (syncing) "Synchronisiere …" else "Jetzt synchronisieren")
                }
                OutlinedButton(onClick = onDisconnect, enabled = !disconnecting) {
                    Icon(Icons.Default.DeleteOutline, "Verbindung entfernen")
                }
            }
        }
    }
}

@Composable
private fun PartialDataNotice(onRetry: () -> Unit) {
    Surface(shape = MaterialTheme.shapes.medium, color = MaterialTheme.colorScheme.errorContainer) {
        Row(
            Modifier.fillMaxWidth().padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Icon(Icons.Default.Warning, null)
            Text("Einige Gesundheitsbereiche konnten nicht geladen werden.", Modifier.weight(1f))
            TextButton(onClick = onRetry) { Text("Erneut") }
        }
    }
}

@Composable
private fun ScoreSection(overview: HealthOverview) {
    val order = listOf("recovery", "energy", "training_load", "resilience")
    val scores = order.mapNotNull(overview.scores::get) + overview.scores
        .filterKeys { it !in order }
        .values
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        if (scores.isEmpty()) {
            EmptyPane(
                "Noch keine belastbaren Scores",
                overview.uncertainty.firstOrNull()
                    ?: "Für eine persönliche Vergleichsbasis werden mehrere Tage mit ausreichend Daten benötigt.",
            )
        } else {
            scores.forEach { ScoreCard(it) }
        }
        overview.uncertainty.forEach { uncertainty ->
            Text(
                "Hinweis: $uncertainty",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun ScoreCard(score: HealthScore) {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.Top) {
                Column(Modifier.weight(1f)) {
                    Text(score.label.ifBlank { healthScoreLabel(score.key) }, style = MaterialTheme.typography.titleMedium)
                    Text(
                        score.level ?: scoreStatusLabel(score.status),
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
                Text(
                    score.value?.let { "$it ${score.unit}" } ?: "–",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.ExtraBold,
                )
            }
            DetailLine("Datenabdeckung", "${decimal(score.dataCoverage.percent)} %")
            DetailLine("Sicherheit", score.confidence.replaceFirstChar { it.uppercase() })
            score.importantFactors.take(3).forEach { factor ->
                val values = buildString {
                    factor.currentValue?.let { append(decimal(it)); factor.unit?.let { unit -> append(" $unit") } }
                    factor.baselineValue?.let {
                        if (isNotEmpty()) append(" · ")
                        append("Basis ${decimal(it)}")
                        factor.baselineWindowDays?.let { days -> append(" / $days Tage") }
                    }
                }
                Text(
                    "• ${factor.label.ifBlank { factor.key }}${values.takeIf(String::isNotBlank)?.let { ": $it" }.orEmpty()}",
                    style = MaterialTheme.typography.bodySmall,
                )
            }
            if (score.dataCoverage.missingRequiredSignals.isNotEmpty()) {
                Text(
                    "Fehlend: ${score.dataCoverage.missingRequiredSignals.joinToString { healthMetricLabel(it) }}",
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }
    }
}

@Composable
private fun HealthDataSection(data: HealthData) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        val latest = data.metrics.distinctBy { it.metricType }.take(8)
        if (latest.isNotEmpty()) {
            Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                    Text("Messwerte", style = MaterialTheme.typography.titleMedium)
                    latest.forEach { MetricLine(it) }
                }
            }
        }
        data.heartRate.firstOrNull()?.let { heartRate ->
            DataSummaryCard(
                icon = Icons.Default.MonitorHeart,
                title = "Herzfrequenz",
                value = "Ø ${decimal(heartRate.averageBpm)} bpm",
                detail = "${decimal(heartRate.minBpm)}–${decimal(heartRate.maxBpm)} bpm · ${heartRate.granularity}",
            )
        }
        data.sleeps.firstOrNull()?.let { SleepCard(it) }
        data.exercises.firstOrNull()?.let { ExerciseCard(it) }
        if (data.isEmpty) {
            EmptyPane("Keine Messwerte im Zeitraum", "Google hat für den aktuellen Abruf keine Daten geliefert.")
        }
    }
}

@Composable
private fun MetricLine(metric: HealthMetric) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(healthMetricLabel(metric.metricType), Modifier.weight(1f))
        Text("${decimal(metric.value)} ${metric.unit}", fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun SleepCard(sleep: HealthSleepSession) {
    val duration = sleep.minutesAsleep?.let { (it * 60.0).asDuration() } ?: "Dauer unbekannt"
    DataSummaryCard(
        icon = Icons.Default.Bedtime,
        title = if (sleep.isNap) "Letzter Schlaf (Nickerchen)" else "Letzter Schlaf",
        value = duration,
        detail = "Ende ${sleep.endAt.asGermanDateTime()} · ${sleep.stages.size} Schlafphasen" +
            if (sleep.overlapsOtherSession) " · Überlappung erkannt" else "",
    )
}

@Composable
private fun ExerciseCard(exercise: HealthExercise) {
    val detail = listOfNotNull(
        exercise.distanceMeters?.asDistance(),
        exercise.activeDurationSeconds?.asDuration(),
        exercise.averageHeartRateBpm?.let { "Ø $it bpm" },
    ).joinToString(" · ")
    DataSummaryCard(
        icon = Icons.AutoMirrored.Filled.DirectionsRun,
        title = exercise.title ?: healthMetricLabel(exercise.exerciseType),
        value = exercise.startAt.asGermanDateTime(),
        detail = detail.ifBlank { "Training aus Google Health" },
    )
}

@Composable
private fun DataSummaryCard(icon: ImageVector, title: String, value: String, detail: String) {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
        Row(Modifier.fillMaxWidth().padding(16.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Icon(icon, null, tint = MaterialTheme.colorScheme.primary)
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Text(title, style = MaterialTheme.typography.titleMedium)
                Text(value, fontWeight = FontWeight.Bold)
                Text(
                    detail,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}

@Composable
private fun SectionTitle(title: String, icon: ImageVector) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(9.dp)) {
        Icon(icon, null, tint = MaterialTheme.colorScheme.primary)
        Text(title, style = MaterialTheme.typography.titleLarge)
    }
}

@Composable
private fun StatusLabel(status: String) {
    Surface(shape = MaterialTheme.shapes.extraSmall, color = MaterialTheme.colorScheme.primaryContainer) {
        Text(
            healthStatusLabel(status),
            Modifier.padding(horizontal = 9.dp, vertical = 5.dp),
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onPrimaryContainer,
        )
    }
}

@Composable
private fun DetailLine(label: String, value: String) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.weight(1f))
        Spacer(Modifier.width(12.dp))
        Text(value, fontWeight = FontWeight.SemiBold)
    }
}

private fun healthStatusLabel(value: String): String = when (value.lowercase()) {
    "connected" -> "Aktiv"
    "reauthorization_required" -> "Neu anmelden"
    "revoked" -> "Widerrufen"
    "error" -> "Fehler"
    else -> value.replace('_', ' ').replaceFirstChar { it.uppercase() }
}

private fun healthScopeLabel(value: String): String = when {
    value.endsWith("activity_and_fitness.readonly") -> "Aktivität & Fitness (lesen)"
    value.endsWith("health_metrics_and_measurements.readonly") -> "Gesundheitsmesswerte (lesen)"
    value.endsWith("sleep.readonly") -> "Schlaf (lesen)"
    else -> value.substringAfterLast('/').replace('_', ' ')
}

private fun healthMetricLabel(value: String): String = when (value.lowercase()) {
    "resting_heart_rate", "resting_heart_rate_bpm" -> "Ruhepuls"
    "hrv_rmssd", "hrv_rmssd_ms" -> "Herzfrequenzvariabilität"
    "respiratory_rate" -> "Atemfrequenz"
    "spo2_average" -> "Sauerstoffsättigung"
    "steps" -> "Schritte"
    "active_energy" -> "Aktive Energie"
    "total_calories" -> "Gesamtkalorien"
    "cycling" -> "Radfahren"
    else -> value.replace('_', ' ').replace('-', ' ').replaceFirstChar { it.uppercase() }
}

private fun healthScoreLabel(value: String): String = when (value) {
    "recovery" -> "Recovery"
    "energy" -> "Energie"
    "training_load" -> "Trainingsbelastung"
    "resilience" -> "Langfristige Resilienz"
    else -> healthMetricLabel(value)
}

private fun scoreStatusLabel(value: String): String = when (value) {
    "available" -> "Berechnet"
    "insufficient_baseline" -> "Vergleichsbasis noch zu klein"
    "insufficient_coverage" -> "Datenabdeckung unzureichend"
    "missing_data" -> "Zentrale Daten fehlen"
    else -> "Noch nicht verfügbar"
}

private fun healthErrorLabel(value: String): String = when (value) {
    "google_reauthorization_required" -> "Erneute Google-Anmeldung erforderlich"
    "missing_google_health_scopes" -> "Lesefreigaben sind unvollständig"
    "health_sync_failed" -> "Letzte Synchronisation fehlgeschlagen"
    else -> value.replace('_', ' ')
}

private val decimalFormat = DecimalFormat("0.#", DecimalFormatSymbols(Locale.GERMANY))

private fun decimal(value: Double): String = synchronized(decimalFormat) { decimalFormat.format(value) }
