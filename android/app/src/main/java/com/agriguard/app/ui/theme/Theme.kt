package com.agriguard.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable

private val AgriGuardColors = darkColorScheme(
    primary = Good,
    onPrimary = Bg,
    secondary = Water,
    background = Bg,
    onBackground = Ink,
    surface = Surface,
    onSurface = Ink,
    surfaceVariant = SurfaceAlt,
    onSurfaceVariant = InkSoft,
    error = Urgent,
    onError = Bg,
    outline = Line,
)

@Composable
fun AgriGuardTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = AgriGuardColors,
        content = content,
    )
}
