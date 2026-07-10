package de.avento.app.ui.theme

import android.app.Activity
import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

private val AventoGreen = Color(0xFF006B56)
private val AventoMint = Color(0xFF9EF2D5)
private val LightColors = lightColorScheme(
    primary = AventoGreen,
    onPrimary = Color.White,
    primaryContainer = Color(0xFF7BF8D1),
    onPrimaryContainer = Color(0xFF002018),
    secondary = Color(0xFF4B635A),
    tertiary = Color(0xFF3E6374),
)
private val DarkColors = darkColorScheme(
    primary = AventoMint,
    onPrimary = Color(0xFF00382C),
    primaryContainer = Color(0xFF00513F),
    onPrimaryContainer = Color(0xFF7BF8D1),
    secondary = Color(0xFFB2CCC0),
    tertiary = Color(0xFFA6CDDF),
)

@Composable
fun AventoTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    dynamicColor: Boolean = true,
    content: @Composable () -> Unit,
) {
    val context = LocalContext.current
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S && darkTheme ->
            dynamicDarkColorScheme(context)
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S ->
            dynamicLightColorScheme(context)
        darkTheme -> DarkColors
        else -> LightColors
    }
    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = !darkTheme
        }
    }
    MaterialTheme(colorScheme = colorScheme, content = content)
}
