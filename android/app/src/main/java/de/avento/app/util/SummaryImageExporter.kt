package de.avento.app.util

import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import androidx.core.content.FileProvider
import de.avento.app.data.model.Activity
import de.avento.app.data.model.ActivityTrack
import java.io.File
import java.io.FileOutputStream
import kotlin.math.min

object SummaryImageExporter {
    fun share(context: Context, activity: Activity, track: ActivityTrack?) {
        val bitmap = render(activity, track)
        val directory = File(context.cacheDir, "shared").apply { mkdirs() }
        val file = File(directory, "avento-${activity.id}.png")
        FileOutputStream(file).use { bitmap.compress(Bitmap.CompressFormat.PNG, 95, it) }
        bitmap.recycle()
        val uri = FileProvider.getUriForFile(context, "${context.packageName}.files", file)
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = "image/png"
            putExtra(Intent.EXTRA_STREAM, uri)
            putExtra(Intent.EXTRA_TEXT, "${activity.title ?: "Radfahrt"} · ${activity.distanceMeters.asDistance()}")
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        context.startActivity(Intent.createChooser(intent, "Aktivität teilen"))
    }

    internal fun render(activity: Activity, track: ActivityTrack?): Bitmap {
        val width = 1080
        val height = 1350
        val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        val paint = Paint(Paint.ANTI_ALIAS_FLAG)
        canvas.drawColor(Color.rgb(5, 39, 31))

        paint.color = Color.rgb(158, 242, 213)
        paint.textSize = 48f
        paint.isFakeBoldText = true
        canvas.drawText("AVENTO", 72f, 92f, paint)

        paint.color = Color.WHITE
        paint.textSize = 68f
        canvas.drawText((activity.title ?: "Radfahrt").take(28), 72f, 190f, paint)
        paint.textSize = 30f
        paint.isFakeBoldText = false
        paint.color = Color.rgb(190, 215, 205)
        canvas.drawText(activity.startedAt.asGermanDateTime(), 72f, 242f, paint)

        drawRoute(canvas, paint, track, 72f, 295f, 936f, 525f)

        metric(canvas, paint, "DISTANZ", activity.distanceMeters.asDistance(), 72f, 900f)
        metric(canvas, paint, "BEWEGUNGSZEIT", activity.movingTimeSeconds.asDuration(), 390f, 900f)
        metric(canvas, paint, "HÖHENMETER", activity.elevationGainMeters.asElevation(), 745f, 900f)
        metric(canvas, paint, "Ø GESCHWINDIGKEIT", activity.averageSpeedMps.asSpeed(), 72f, 1060f)
        metric(canvas, paint, "Ø HERZFREQUENZ", activity.averageHeartRate.asInteger("bpm"), 390f, 1060f)
        metric(canvas, paint, "Ø LEISTUNG", activity.averagePower.asInteger("W"), 745f, 1060f)

        paint.color = Color.rgb(190, 215, 205)
        paint.textSize = 27f
        val summary = activity.aiSummary?.replace('\n', ' ')?.take(150)
        if (!summary.isNullOrBlank()) drawWrappedText(canvas, paint, "KI: $summary", 72f, 1205f, 936f)
        paint.color = Color.rgb(158, 242, 213)
        paint.textSize = 24f
        canvas.drawText("Erstellt mit Avento", 72f, 1300f, paint)
        return bitmap
    }

    private fun drawRoute(
        canvas: Canvas,
        paint: Paint,
        track: ActivityTrack?,
        left: Float,
        top: Float,
        width: Float,
        height: Float,
    ) {
        paint.color = Color.rgb(12, 70, 56)
        canvas.drawRoundRect(left, top, left + width, top + height, 36f, 36f, paint)
        val points = track?.points?.mapNotNull { point ->
            val lat = point.latitude ?: return@mapNotNull null
            val lon = point.longitude ?: return@mapNotNull null
            lon to lat
        }.orEmpty()
        if (points.size < 2) {
            paint.color = Color.rgb(190, 215, 205)
            paint.textSize = 34f
            canvas.drawText("Keine GPS-Strecke verfügbar", left + 48f, top + height / 2, paint)
            return
        }
        val minX = points.minOf { it.first }
        val maxX = points.maxOf { it.first }
        val minY = points.minOf { it.second }
        val maxY = points.maxOf { it.second }
        val rangeX = (maxX - minX).takeIf { it > 0.000001 } ?: 1.0
        val rangeY = (maxY - minY).takeIf { it > 0.000001 } ?: 1.0
        val padding = 55f
        val path = Path()
        points.forEachIndexed { index, (xValue, yValue) ->
            val x = left + padding + ((xValue - minX) / rangeX).toFloat() * (width - 2 * padding)
            val y = top + padding + (1f - ((yValue - minY) / rangeY).toFloat()) * (height - 2 * padding)
            if (index == 0) path.moveTo(x, y) else path.lineTo(x, y)
        }
        paint.style = Paint.Style.STROKE
        paint.strokeWidth = 10f
        paint.strokeCap = Paint.Cap.ROUND
        paint.strokeJoin = Paint.Join.ROUND
        paint.color = Color.rgb(158, 242, 213)
        canvas.drawPath(path, paint)
        paint.style = Paint.Style.FILL
    }

    private fun metric(canvas: Canvas, paint: Paint, label: String, value: String, x: Float, y: Float) {
        paint.color = Color.rgb(190, 215, 205)
        paint.textSize = 23f
        paint.isFakeBoldText = false
        canvas.drawText(label, x, y, paint)
        paint.color = Color.WHITE
        paint.textSize = 41f
        paint.isFakeBoldText = true
        canvas.drawText(value, x, y + 55f, paint)
        paint.isFakeBoldText = false
    }

    private fun drawWrappedText(canvas: Canvas, paint: Paint, text: String, x: Float, y: Float, maxWidth: Float) {
        var remaining = text
        var lineY = y
        repeat(2) {
            if (remaining.isBlank()) return
            val count = min(remaining.length, paint.breakText(remaining, true, maxWidth, null))
            val safeBreak = remaining.lastIndexOf(' ', count.coerceAtMost(remaining.lastIndex))
                .takeIf { it > 0 } ?: count
            canvas.drawText(remaining.take(safeBreak), x, lineY, paint)
            remaining = remaining.drop(safeBreak).trimStart()
            lineY += paint.textSize * 1.25f
        }
    }
}
