package de.avento.app.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.dp
import de.avento.app.data.model.TrackPoint
import java.util.Locale

@Composable
fun LineChart(
    title: String,
    values: List<Double?>,
    unit: String,
    modifier: Modifier = Modifier,
) {
    val points = values.mapIndexedNotNull { index, value -> value?.let { index to it } }
    if (points.size < 2) return
    val min = points.minOf { it.second }
    val max = points.maxOf { it.second }
    val range = (max - min).takeIf { it > 0.0001 } ?: 1.0
    val lineColor = MaterialTheme.colorScheme.primary
    val gridColor = MaterialTheme.colorScheme.outlineVariant
    Column(modifier) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(title, style = MaterialTheme.typography.titleMedium)
            Text(
                "${String.format(Locale.GERMANY, "%.1f", min)}–${String.format(Locale.GERMANY, "%.1f", max)} $unit",
                style = MaterialTheme.typography.labelMedium,
            )
        }
        Canvas(
            Modifier
                .fillMaxWidth()
                .height(140.dp)
                .padding(top = 12.dp),
        ) {
            repeat(4) { index ->
                val y = size.height * index / 3f
                drawLine(gridColor, Offset(0f, y), Offset(size.width, y), strokeWidth = 1f)
            }
            val denominator = (values.lastIndex).coerceAtLeast(1).toFloat()
            val path = Path()
            points.forEachIndexed { pointIndex, (sourceIndex, value) ->
                val x = sourceIndex / denominator * size.width
                val y = size.height - ((value - min) / range).toFloat() * size.height
                if (pointIndex == 0) path.moveTo(x, y) else path.lineTo(x, y)
            }
            drawPath(path, lineColor, style = Stroke(width = 4f, cap = StrokeCap.Round))
        }
    }
}

@Composable
fun RoutePreview(points: List<TrackPoint>, modifier: Modifier = Modifier) {
    val geo = points.mapNotNull { point ->
        val latitude = point.latitude ?: return@mapNotNull null
        val longitude = point.longitude ?: return@mapNotNull null
        longitude to latitude
    }
    if (geo.size < 2) return
    val minX = geo.minOf { it.first }
    val maxX = geo.maxOf { it.first }
    val minY = geo.minOf { it.second }
    val maxY = geo.maxOf { it.second }
    val rangeX = (maxX - minX).takeIf { it > 0.000001 } ?: 1.0
    val rangeY = (maxY - minY).takeIf { it > 0.000001 } ?: 1.0
    val routeColor = MaterialTheme.colorScheme.primary
    val surfaceColor = MaterialTheme.colorScheme.surfaceVariant
    Canvas(modifier.fillMaxWidth().height(220.dp)) {
        drawRect(surfaceColor)
        val padding = 24f
        val path = Path()
        geo.forEachIndexed { index, (longitude, latitude) ->
            val x = padding + ((longitude - minX) / rangeX).toFloat() * (size.width - padding * 2)
            val y = padding + (1f - ((latitude - minY) / rangeY).toFloat()) * (size.height - padding * 2)
            if (index == 0) path.moveTo(x, y) else path.lineTo(x, y)
        }
        drawPath(path, routeColor, style = Stroke(width = 7f, cap = StrokeCap.Round))
    }
}
