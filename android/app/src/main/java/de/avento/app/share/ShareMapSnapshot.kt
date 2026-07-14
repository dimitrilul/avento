package de.avento.app.share

import android.content.Context
import android.graphics.Bitmap
import de.avento.app.data.model.TrackPoint
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withTimeoutOrNull
import org.maplibre.android.geometry.LatLng
import org.maplibre.android.geometry.LatLngBounds
import org.maplibre.android.maps.Style
import org.maplibre.android.snapshotter.MapSnapshotter
import kotlin.coroutines.resume

private const val SHARE_MAP_STYLE = "https://tiles.openfreemap.org/styles/liberty"

suspend fun createShareMapSnapshot(context: Context, points: List<TrackPoint>, width: Int, height: Int): Bitmap? {
    val coordinates = points.mapNotNull { point ->
        val latitude = point.latitude ?: return@mapNotNull null
        val longitude = point.longitude ?: return@mapNotNull null
        LatLng(latitude, longitude)
    }
    if (coordinates.size < 2) return null
    val bounds = LatLngBounds.Builder().apply { coordinates.forEach(::include) }.build()
    return withTimeoutOrNull(8_000) {
        suspendCancellableCoroutine { continuation ->
            val options = MapSnapshotter.Options(width.coerceAtMost(1920), height.coerceAtMost(1920))
                .withStyleBuilder(Style.Builder().fromUri(SHARE_MAP_STYLE))
                .withRegion(bounds)
                .withPixelRatio(1f)
            val snapshotter = MapSnapshotter(context.applicationContext, options)
            snapshotter.setPadding(70, 70, 70, 70)
            continuation.invokeOnCancellation { snapshotter.cancel() }
            snapshotter.start(
                { snapshot -> if (continuation.isActive) continuation.resume(snapshot.bitmap) },
                { if (continuation.isActive) continuation.resume(null) },
            )
        }
    }
}
