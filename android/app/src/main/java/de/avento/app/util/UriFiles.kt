package de.avento.app.util

import android.content.ContentResolver
import android.net.Uri
import android.provider.OpenableColumns
import java.io.ByteArrayOutputStream

private const val MAX_ACTIVITY_BYTES = 50 * 1024 * 1024
private const val MAX_PHOTO_BYTES = 20 * 1024 * 1024
private const val MAX_AVATAR_BYTES = 10 * 1024 * 1024

data class LocalFile(
    val bytes: ByteArray,
    val displayName: String,
    val contentType: String,
)

fun ContentResolver.displayName(uri: Uri): String? = runCatching {
    query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { cursor ->
        if (cursor.moveToFirst()) cursor.getString(0) else null
    }
}.getOrNull()

fun ContentResolver.readActivity(uri: Uri): ByteArray {
    return readLimited(uri, MAX_ACTIVITY_BYTES, "Die Aktivitätsdatei darf höchstens 50 MB groß sein.")
}

fun ContentResolver.readPhoto(uri: Uri): LocalFile = LocalFile(
    bytes = readLimited(uri, MAX_PHOTO_BYTES, "Das Foto darf höchstens 20 MB groß sein."),
    displayName = displayName(uri) ?: "foto.jpg",
    contentType = getType(uri)?.takeIf { it.startsWith("image/") } ?: "image/jpeg",
)

fun ContentResolver.readAvatar(uri: Uri): LocalFile = LocalFile(
    bytes = readLimited(uri, MAX_AVATAR_BYTES, "Das Profilbild darf höchstens 10 MB groß sein."),
    displayName = displayName(uri) ?: "profilbild.jpg",
    contentType = getType(uri)?.takeIf { it.startsWith("image/") } ?: "image/jpeg",
)

private fun ContentResolver.readLimited(uri: Uri, maximumBytes: Int, sizeMessage: String): ByteArray {
    val size = runCatching {
        query(uri, arrayOf(OpenableColumns.SIZE), null, null, null)?.use { cursor ->
            if (cursor.moveToFirst() && !cursor.isNull(0)) cursor.getLong(0) else null
        }
    }.getOrNull()
    require(size == null || size <= maximumBytes) { sizeMessage }

    return openInputStream(uri)?.use { input ->
        val output = ByteArrayOutputStream()
        val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
        var total = 0
        while (true) {
            val count = input.read(buffer)
            if (count < 0) break
            total += count
            require(total <= maximumBytes) { sizeMessage }
            output.write(buffer, 0, count)
        }
        output.toByteArray()
    } ?: error("Die ausgewählte Datei kann nicht gelesen werden.")
}
