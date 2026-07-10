package de.avento.app.util

import android.content.ContentResolver
import android.net.Uri
import android.provider.OpenableColumns
import java.io.ByteArrayOutputStream

private const val MAX_TCX_BYTES = 50 * 1024 * 1024

fun ContentResolver.displayName(uri: Uri): String? = runCatching {
    query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { cursor ->
        if (cursor.moveToFirst()) cursor.getString(0) else null
    }
}.getOrNull()

fun ContentResolver.readTcx(uri: Uri): ByteArray {
    val size = runCatching {
        query(uri, arrayOf(OpenableColumns.SIZE), null, null, null)?.use { cursor ->
            if (cursor.moveToFirst() && !cursor.isNull(0)) cursor.getLong(0) else null
        }
    }.getOrNull()
    require(size == null || size <= MAX_TCX_BYTES) { "Die TCX-Datei darf höchstens 50 MB groß sein." }

    return openInputStream(uri)?.use { input ->
        val output = ByteArrayOutputStream()
        val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
        var total = 0
        while (true) {
            val count = input.read(buffer)
            if (count < 0) break
            total += count
            require(total <= MAX_TCX_BYTES) { "Die TCX-Datei darf höchstens 50 MB groß sein." }
            output.write(buffer, 0, count)
        }
        output.toByteArray()
    } ?: error("Die ausgewählte Datei kann nicht gelesen werden.")
}
