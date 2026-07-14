package de.avento.app.share

import org.junit.Assert.assertEquals
import org.junit.Test

class OverlayContractTest {
    @Test
    fun `all social formats use the expected export size`() {
        assertEquals(1080 to 1080, OverlayFormat.SQUARE.width to OverlayFormat.SQUARE.height)
        assertEquals(1080 to 1350, OverlayFormat.PORTRAIT.width to OverlayFormat.PORTRAIT.height)
        assertEquals(1080 to 1920, OverlayFormat.STORY.width to OverlayFormat.STORY.height)
        assertEquals(1920 to 1080, OverlayFormat.LANDSCAPE.width to OverlayFormat.LANDSCAPE.height)
    }

    @Test
    fun `six distinct templates are registered`() {
        assertEquals(listOf("Classic", "Minimal", "Photo", "Stats", "Map", "Achievement"), OverlayTemplate.entries.map { it.label })
    }
}
