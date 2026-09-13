package com.agriguard.app.screens

import android.media.MediaPlayer
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material.icons.filled.VolumeUp
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.agriguard.app.AppLanguage
import com.agriguard.app.network.ApiClient
import com.agriguard.app.ui.theme.Good
import com.agriguard.app.ui.theme.GoodSoft
import com.agriguard.app.ui.theme.Urgent
import com.agriguard.app.ui.theme.UrgentSoft

@Composable
fun HealthPill(isHealthy: Boolean) {
    val bg = if (isHealthy) GoodSoft else UrgentSoft
    val fg = if (isHealthy) Good else Urgent
    Text(
        text = if (isHealthy) "HEALTHY" else "DISEASED",
        color = fg,
        style = MaterialTheme.typography.labelSmall,
        modifier = Modifier
            .background(bg, RoundedCornerShape(100))
            .padding(horizontal = 10.dp, vertical = 4.dp),
    )
}

@Composable
fun VoiceReportButton(modifier: Modifier = Modifier) {
    val context = LocalContext.current
    var player by remember { mutableStateOf<MediaPlayer?>(null) }
    var state by remember { mutableStateOf("idle") } // idle | loading | playing | error

    DisposableEffect(Unit) {
        onDispose {
            player?.release()
            player = null
        }
    }

    fun stop() {
        player?.release()
        player = null
        state = "idle"
    }

    fun play() {
        state = "loading"
        val mp = MediaPlayer()
        mp.setOnPreparedListener {
            state = "playing"
            it.start()
        }
        mp.setOnCompletionListener { stop() }
        mp.setOnErrorListener { _, _, _ -> state = "error"; true }
        try {
            mp.setDataSource(context, android.net.Uri.parse(ApiClient.voiceReportUrl(AppLanguage.current)))
            mp.prepareAsync()
            player = mp
        } catch (e: Exception) {
            state = "error"
        }
    }

    Button(
        onClick = { if (state == "playing" || state == "loading") stop() else play() },
        modifier = modifier.fillMaxWidth(),
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Icon(
                if (state == "playing" || state == "loading") Icons.Filled.Stop else Icons.Filled.VolumeUp,
                contentDescription = null,
            )
            Text(
                when (state) {
                    "loading" -> "Loading..."
                    "playing" -> "Stop Voice Report"
                    "error" -> "Retry Voice Report"
                    else -> if (AppLanguage.current == "ta") "Play Voice Report (Tamil)" else "Play Voice Report (English)"
                }
            )
        }
    }
}
