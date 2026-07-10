package de.avento.app.settings

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class ServerConfigStoreTest {
    @Test
    fun `normalizes host and adds api path`() {
        assertEquals(
            "https://avento.example.de/api/v1/",
            normalizeServerUrl("avento.example.de"),
        )
        assertEquals(
            "http://192.168.1.20:8000/api/v1/",
            normalizeServerUrl("http://192.168.1.20:8000/"),
        )
    }

    @Test
    fun `keeps existing api path and rejects unsupported schemes`() {
        assertEquals(
            "https://avento.example.de/api/v1/",
            normalizeServerUrl("https://avento.example.de/api/v1"),
        )
        assertThrows(IllegalArgumentException::class.java) {
            normalizeServerUrl("ftp://avento.example.de")
        }
    }
}
