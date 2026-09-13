package com.agriguard.app.screens

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil3.compose.AsyncImage
import com.agriguard.app.AppLanguage
import com.agriguard.app.network.ApiClient
import com.agriguard.app.network.LiveResult
import com.agriguard.app.ui.theme.Beta
import com.agriguard.app.ui.theme.InkFaint
import com.agriguard.app.ui.theme.SurfaceAlt
import com.agriguard.app.ui.theme.Urgent
import kotlinx.coroutines.delay

@Composable
fun LiveScreen() {
    var result by remember { mutableStateOf<LiveResult?>(null) }
    var cacheBuster by remember { mutableStateOf(0L) }
    var error by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(Unit) {
        while (true) {
            try {
                result = ApiClient.getLive()
                cacheBuster = System.currentTimeMillis()
                error = null
            } catch (e: Exception) {
                error = e.message ?: "Failed to load"
            }
            delay(1200)
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("MULTI-CROP SPECIALIST MODEL", color = Beta, style = MaterialTheme.typography.labelSmall)
        Text("Live", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        Text(
            "Most recent frame from the camera device, with the AI's verdict.",
            color = InkFaint,
            style = MaterialTheme.typography.bodySmall,
        )

        Box(
            modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(4f / 3f)
                .background(SurfaceAlt, RoundedCornerShape(16.dp)),
        ) {
            if (result != null) {
                AsyncImage(
                    model = ApiClient.frameImageUrl(cacheBuster),
                    contentDescription = "Latest captured frame",
                    contentScale = ContentScale.Crop,
                    modifier = Modifier
                        .fillMaxSize()
                        .background(SurfaceAlt, RoundedCornerShape(16.dp)),
                )
                LiveBadge(modifier = Modifier.align(Alignment.TopStart).padding(12.dp))
            } else {
                Text(
                    "Waiting for the first frame from the camera device...",
                    color = InkFaint,
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.align(Alignment.Center).padding(horizontal = 20.dp),
                )
            }
        }

        Card(
            shape = RoundedCornerShape(14.dp),
            colors = CardDefaults.cardColors(containerColor = SurfaceAlt),
        ) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                result?.let { r ->
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text(r.position, style = MaterialTheme.typography.labelMedium, color = InkFaint)
                        Text(r.timestamp, style = MaterialTheme.typography.labelSmall, color = InkFaint)
                    }
                    val isTa = AppLanguage.current == "ta"
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text(if (isTa) r.labelDisplayTa else r.labelDisplay, fontWeight = FontWeight.Bold)
                        HealthPill(r.isHealthy)
                    }
                    Text("${r.confidence}% confidence", color = InkFaint, style = MaterialTheme.typography.bodySmall)
                    (if (isTa) r.treatmentTa else r.treatment)?.let { Text("Do this: $it", style = MaterialTheme.typography.bodySmall) }
                    Text("Next pass: ${if (isTa) r.recommendedActionLabelTa else r.recommendedActionLabel}", style = MaterialTheme.typography.labelMedium)
                } ?: Text("Waiting for the first detection...", color = InkFaint)
                error?.let { Text("Error: $it", color = MaterialTheme.colorScheme.error) }
            }
        }
    }
}

@Composable
private fun LiveBadge(modifier: Modifier = Modifier) {
    val transition = rememberInfiniteTransition(label = "live-pulse")
    val pulseAlpha by transition.animateFloat(
        initialValue = 1f,
        targetValue = 0.3f,
        animationSpec = infiniteRepeatable(
            animation = tween(700),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "live-pulse-alpha",
    )

    Row(
        modifier = modifier
            .background(Color.Black.copy(alpha = 0.55f), RoundedCornerShape(100))
            .padding(horizontal = 10.dp, vertical = 5.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Box(
            modifier = Modifier
                .size(7.dp)
                .alpha(pulseAlpha)
                .background(Urgent, CircleShape),
        )
        Text("LIVE", color = Color.White, fontSize = 11.sp, fontWeight = FontWeight.Medium)
    }
}
