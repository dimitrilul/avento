package de.avento.app.util

import java.time.Instant
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.time.format.FormatStyle
import java.util.Locale
import kotlin.math.roundToInt

fun Double?.asDistance(): String = this?.let { String.format(Locale.GERMANY, "%.1f km", it / 1000.0) } ?: "–"

fun Double?.asElevation(): String = this?.let { "${it.roundToInt()} hm" } ?: "–"

fun Double?.asSpeed(): String = this?.let { String.format(Locale.GERMANY, "%.1f km/h", it * 3.6) } ?: "–"

fun Double?.asInteger(unit: String): String = this?.let { "${it.roundToInt()} $unit" } ?: "–"

fun Double?.asDuration(): String {
    if (this == null) return "–"
    val total = roundToInt().coerceAtLeast(0)
    val hours = total / 3600
    val minutes = total % 3600 / 60
    val seconds = total % 60
    return if (hours > 0) "%d:%02d:%02d h".format(hours, minutes, seconds)
    else "%d:%02d min".format(minutes, seconds)
}

fun String?.asGermanDateTime(): String {
    if (this.isNullOrBlank()) return "Datum unbekannt"
    val zone = ZoneId.systemDefault()
    val value = runCatching { OffsetDateTime.parse(this).atZoneSameInstant(zone) }
        .recoverCatching { Instant.parse(this).atZone(zone) }
        .getOrNull() ?: return this
    return DateTimeFormatter.ofLocalizedDateTime(FormatStyle.MEDIUM, FormatStyle.SHORT)
        .withLocale(Locale.GERMANY)
        .format(value)
}
