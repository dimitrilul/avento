package de.avento.app.util

import org.junit.Assert.assertEquals
import org.junit.Test

class FormattersTest {
    @Test fun `distance uses kilometres and German decimal separator`() {
        assertEquals("42,2 km", 42_195.0.asDistance())
    }

    @Test fun `duration includes hours`() {
        assertEquals("1:02:03 h", 3723.0.asDuration())
    }

    @Test fun `metres per second are converted to kilometres per hour`() {
        assertEquals("36,0 km/h", 10.0.asSpeed())
    }
}
