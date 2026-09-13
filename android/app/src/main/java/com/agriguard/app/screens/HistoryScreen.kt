package com.agriguard.app.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.agriguard.app.AppLanguage
import com.agriguard.app.network.ApiClient
import com.agriguard.app.network.Detection
import com.agriguard.app.network.Summary
import com.agriguard.app.ui.theme.Good
import com.agriguard.app.ui.theme.Ink
import com.agriguard.app.ui.theme.InkFaint
import com.agriguard.app.ui.theme.SurfaceAlt
import com.agriguard.app.ui.theme.Urgent
import kotlinx.coroutines.delay

@Composable
fun HistoryScreen() {
    var detections by remember { mutableStateOf<List<Detection>>(emptyList()) }
    var summary by remember { mutableStateOf<Summary?>(null) }
    var loading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(Unit) {
        while (true) {
            try {
                detections = ApiClient.getDetections()
                summary = ApiClient.getSummary()
                error = null
            } catch (e: Exception) {
                error = e.message ?: "Failed to load"
            } finally {
                loading = false
            }
            delay(5000)
        }
    }

    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Results", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        Text("Every detection logged by this app (multi-crop model).", color = InkFaint, style = MaterialTheme.typography.bodySmall)

        summary?.let { s ->
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                StatChip("Total", s.totalDetections.toString(), Ink, Modifier.weight(1f))
                StatChip("Healthy", s.healthyCount.toString(), Good, Modifier.weight(1f))
                StatChip("Diseased", s.diseasedCount.toString(), Urgent, Modifier.weight(1f))
            }
        }

        VoiceReportButton()

        when {
            loading -> CircularProgressIndicator()
            error != null -> Text("Error: $error", color = MaterialTheme.colorScheme.error)
            detections.isEmpty() -> Text("No detections yet -- capture a frame first.", color = InkFaint)
            else -> LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                items(detections) { d -> DetectionRow(d) }
            }
        }
    }
}

@Composable
private fun StatChip(label: String, value: String, valueColor: androidx.compose.ui.graphics.Color, modifier: Modifier = Modifier) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = SurfaceAlt),
    ) {
        Column(Modifier.padding(vertical = 12.dp, horizontal = 10.dp)) {
            Text(value, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, color = valueColor)
            Text(label, style = MaterialTheme.typography.labelSmall, color = InkFaint)
        }
    }
}

@Composable
fun DetectionRow(d: Detection) {
    Card(
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = SurfaceAlt),
    ) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(d.position, style = MaterialTheme.typography.labelMedium, color = InkFaint)
                Text(d.timestamp, style = MaterialTheme.typography.labelSmall, color = InkFaint)
            }
            val isTa = AppLanguage.current == "ta"
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(if (isTa) d.labelDisplayTa else d.labelDisplay, fontWeight = FontWeight.Bold)
                HealthPill(d.isHealthy)
            }
            Text("${d.confidence}% confidence", style = MaterialTheme.typography.bodySmall, color = InkFaint)
            (if (isTa) d.treatmentTa else d.treatment)?.let { Text("Do this: $it", style = MaterialTheme.typography.bodySmall) }
        }
    }
}
