package de.avento.app.ui.theme

import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.view.WindowCompat

/** Feste Markenfarben, die Web und Android miteinander verbinden. */
object AventoPalette {
    val Teal = Color(0xFF0E6562)
    val DeepTeal = Color(0xFF083B3A)
    val Lime = Color(0xFFA5C838)
    val Amber = Color(0xFFE9A23B)
    val Coral = Color(0xFFE26D5A)
    val Blue = Color(0xFF4D82BC)
}

private val LightColors = lightColorScheme(
    primary = AventoPalette.Teal,
    onPrimary = Color.White,
    primaryContainer = Color(0xFFD6EEEA),
    onPrimaryContainer = AventoPalette.DeepTeal,
    secondary = Color(0xFF637C16),
    onSecondary = Color.White,
    secondaryContainer = Color(0xFFE3F3AD),
    onSecondaryContainer = Color(0xFF263500),
    tertiary = AventoPalette.Blue,
    onTertiary = Color.White,
    tertiaryContainer = Color(0xFFD9E9FF),
    onTertiaryContainer = Color(0xFF153B63),
    background = Color(0xFFF5F7F3),
    onBackground = Color(0xFF172322),
    surface = Color(0xFFFFFFFF),
    onSurface = Color(0xFF172322),
    surfaceVariant = Color(0xFFE9EEEA),
    onSurfaceVariant = Color(0xFF61706E),
    outline = Color(0xFF81918E),
    outlineVariant = Color(0xFFDCE4E1),
    error = Color(0xFFBA1A1A),
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFF8FD2CD),
    onPrimary = Color(0xFF003735),
    primaryContainer = Color(0xFF0B4E4C),
    onPrimaryContainer = Color(0xFFC4F0EB),
    secondary = Color(0xFFC5DE77),
    onSecondary = Color(0xFF303F00),
    secondaryContainer = Color(0xFF465A00),
    onSecondaryContainer = Color(0xFFE3F3AD),
    tertiary = Color(0xFFA8C8F1),
    onTertiary = Color(0xFF0C345D),
    tertiaryContainer = Color(0xFF274C73),
    onTertiaryContainer = Color(0xFFD6E7FF),
    background = Color(0xFF0D1615),
    onBackground = Color(0xFFDFE8E5),
    surface = Color(0xFF121D1B),
    onSurface = Color(0xFFDFE8E5),
    surfaceVariant = Color(0xFF263330),
    onSurfaceVariant = Color(0xFFBBCAC6),
    outline = Color(0xFF859591),
    outlineVariant = Color(0xFF3B4946),
    error = Color(0xFFFFB4AB),
)

private val AventoTypography = Typography(
    displaySmall = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.ExtraBold,
        fontSize = 38.sp,
        lineHeight = 44.sp,
        letterSpacing = (-1.2).sp,
    ),
    headlineLarge = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.ExtraBold,
        fontSize = 32.sp,
        lineHeight = 38.sp,
        letterSpacing = (-0.8).sp,
    ),
    headlineMedium = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Bold,
        fontSize = 27.sp,
        lineHeight = 33.sp,
        letterSpacing = (-0.55).sp,
    ),
    headlineSmall = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Bold,
        fontSize = 23.sp,
        lineHeight = 29.sp,
        letterSpacing = (-0.35).sp,
    ),
    titleLarge = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Bold,
        fontSize = 20.sp,
        lineHeight = 26.sp,
        letterSpacing = (-0.2).sp,
    ),
    titleMedium = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Bold,
        fontSize = 16.sp,
        lineHeight = 22.sp,
    ),
    titleSmall = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.SemiBold,
        fontSize = 14.sp,
        lineHeight = 20.sp,
    ),
    bodyLarge = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Normal,
        fontSize = 16.sp,
        lineHeight = 24.sp,
    ),
    bodyMedium = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Normal,
        fontSize = 14.sp,
        lineHeight = 21.sp,
    ),
    bodySmall = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Normal,
        fontSize = 12.sp,
        lineHeight = 18.sp,
    ),
    labelLarge = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Bold,
        fontSize = 14.sp,
        lineHeight = 20.sp,
    ),
    labelMedium = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.SemiBold,
        fontSize = 12.sp,
        lineHeight = 17.sp,
    ),
    labelSmall = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.SemiBold,
        fontSize = 11.sp,
        lineHeight = 15.sp,
    ),
)

private val AventoShapes = Shapes(
    extraSmall = RoundedCornerShape(8.dp),
    small = RoundedCornerShape(12.dp),
    medium = RoundedCornerShape(16.dp),
    large = RoundedCornerShape(20.dp),
    extraLarge = RoundedCornerShape(28.dp),
)

@Composable
fun AventoTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            WindowCompat.getInsetsController(window, view).apply {
                isAppearanceLightStatusBars = !darkTheme
                isAppearanceLightNavigationBars = !darkTheme
            }
        }
    }
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        typography = AventoTypography,
        shapes = AventoShapes,
        content = content,
    )
}
