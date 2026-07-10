package de.avento.app.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Fill
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import de.avento.app.data.model.TrackPoint
import java.util.Locale

@Composable
fun LineChart(
    title: String,
    values: List<Double?>,
    unit: String,
    modifier: Modifier = Modifier,
    color: Color? = null,
    subtitle: String? = null,
    startLabel: String? = null,
    endLabel: String? = null,
) {
    val normalizedValues = if (values.count { it != null } == 1) {
        val value = values.firstNotNullOf { it }
        listOf(value, value)
    } else {
        values
    }
    val points = normalizedValues.mapIndexedNotNull { index, value -> value?.let { index to it } }
    if (points.size < 2) return
    val min = points.minOf { it.second }
    val max = points.maxOf { it.second }
    val average = points.map { it.second }.average()
    val range = (max - min).takeIf { it > 0.0001 } ?: 1.0
    val chartColor = color ?: MaterialTheme.colorScheme.primary
    val gridColor = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.72f)
    val labelColor = MaterialTheme.colorScheme.onSurfaceVariant
    Column(modifier) {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.Top,
        ) {
            Column(Modifier.weight(1f)) {
                Text(title, style = MaterialTheme.typography.titleLarge)
                subtitle?.let {
                    Text(
                        it,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(top = 2.dp),
                    )
                }
            }
            Box(
                Modifier.background(chartColor.copy(alpha = 0.11f), RoundedCornerShape(10.dp))
                    .padding(horizontal = 10.dp, vertical = 6.dp),
            ) {
                Text(
                    "Ø ${average.decimal()} $unit",
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.Bold,
                    color = chartColor,
                )
            }
        }
        Row(
            Modifier.fillMaxWidth().padding(top = 18.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(max.decimal(), style = MaterialTheme.typography.labelSmall, color = labelColor)
            Text(
                "${min.decimal()}–${max.decimal()} $unit",
                style = MaterialTheme.typography.labelSmall,
                color = labelColor,
            )
        }
        Canvas(Modifier.fillMaxWidth().height(176.dp).padding(top = 5.dp)) {
            repeat(5) { index ->
                val y = size.height * index / 4f
                drawLine(
                    color = gridColor,
                    start = Offset(0f, y),
                    end = Offset(size.width, y),
                    strokeWidth = 1.dp.toPx(),
                )
            }
            val denominator = normalizedValues.lastIndex.coerceAtLeast(1).toFloat()
            val line = Path()
            val area = Path()
            points.forEachIndexed { pointIndex, (sourceIndex, value) ->
                val x = sourceIndex / denominator * size.width
                val y = size.height - ((value - min) / range).toFloat() * (size.height * 0.88f) - size.height * 0.06f
                if (pointIndex == 0) {
                    line.moveTo(x, y)
                    area.moveTo(x, size.height)
                    area.lineTo(x, y)
                } else {
                    line.lineTo(x, y)
                    area.lineTo(x, y)
                }
            }
            val lastX = points.last().first / denominator * size.width
            area.lineTo(lastX, size.height)
            area.close()
            drawPath(
                path = area,
                brush = Brush.verticalGradient(
                    colors = listOf(chartColor.copy(alpha = 0.3f), chartColor.copy(alpha = 0.02f)),
                    startY = 0f,
                    endY = size.height,
                ),
                style = Fill,
            )
            drawPath(
                path = line,
                color = chartColor,
                style = Stroke(
                    width = 3.dp.toPx(),
                    cap = StrokeCap.Round,
                    join = StrokeJoin.Round,
                ),
            )
        }
        if (startLabel != null || endLabel != null) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(startLabel.orEmpty(), style = MaterialTheme.typography.labelSmall, color = labelColor)
                Text(endLabel.orEmpty(), style = MaterialTheme.typography.labelSmall, color = labelColor)
            }
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
    val startColor = MaterialTheme.colorScheme.secondary
    val endColor = Color(0xFFE26D5A)
    val backgroundTop = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.58f)
    val backgroundBottom = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.72f)
    val gridColor = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.08f)
    Canvas(modifier.fillMaxWidth().height(260.dp)) {
        drawRect(Brush.linearGradient(listOf(backgroundTop, backgroundBottom)))
        repeat(7) { index ->
            val x = size.width * index / 6f
            drawLine(gridColor, Offset(x, 0f), Offset(x, size.height), 1.dp.toPx())
        }
        repeat(5) { index ->
            val y = size.height * index / 4f
            drawLine(gridColor, Offset(0f, y), Offset(size.width, y), 1.dp.toPx())
        }
        val padding = 30.dp.toPx()
        val path = Path()
        var first = Offset.Zero
        var last = Offset.Zero
        geo.forEachIndexed { index, (longitude, latitude) ->
            val x = padding + ((longitude - minX) / rangeX).toFloat() * (size.width - padding * 2)
            val y = padding + (1f - ((latitude - minY) / rangeY).toFloat()) * (size.height - padding * 2)
            val offset = Offset(x, y)
            if (index == 0) {
                first = offset
                path.moveTo(x, y)
            } else {
                path.lineTo(x, y)
            }
            last = offset
        }
        drawPath(
            path,
            Color.White.copy(alpha = 0.9f),
            style = Stroke(width = 8.dp.toPx(), cap = StrokeCap.Round, join = StrokeJoin.Round),
        )
        drawPath(
            path,
            routeColor,
            style = Stroke(width = 4.dp.toPx(), cap = StrokeCap.Round, join = StrokeJoin.Round),
        )
        drawCircle(Color.White, radius = 7.dp.toPx(), center = first)
        drawCircle(startColor, radius = 4.5.dp.toPx(), center = first)
        drawCircle(Color.White, radius = 7.dp.toPx(), center = last)
        drawCircle(endColor, radius = 4.5.dp.toPx(), center = last)
    }
}

private fun Double.decimal(): String = String.format(Locale.GERMANY, "%.1f", this)
