package com.agriguard.app.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
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
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.agriguard.app.network.ApiClient
import com.agriguard.app.network.IrrigationEvent
import com.agriguard.app.network.IrrigationSnapshot
import com.agriguard.app.ui.theme.InkFaint
import com.agriguard.app.ui.theme.Line
import com.agriguard.app.ui.theme.SurfaceAlt
import com.agriguard.app.ui.theme.Urgent
import com.agriguard.app.ui.theme.Water
import kotlinx.coroutines.delay

private const val MOISTURE_THRESHOLD = 30

@Composable
fun IrrigationScreen() {
    var snapshot by remember { mutableStateOf<IrrigationSnapshot?>(null) }
    var loading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(Unit) {
        while (true) {
            try {
                snapshot = ApiClient.getIrrigation()
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
        Text("Irrigation", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        Text("Soil moisture readings and pump status.", color = InkFaint, style = MaterialTheme.typography.bodySmall)

        when {
            loading -> CircularProgressIndicator()
            error != null -> Text("Error: $error", color = MaterialTheme.colorScheme.error)
            snapshot?.latest == null -> Text("No irrigation readings yet.", color = InkFaint)
            else -> {
                val latest = snapshot!!.latest!!
                Card(
                    shape = RoundedCornerShape(14.dp),
                    colors = CardDefaults.cardColors(containerColor = SurfaceAlt),
                ) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Text("Latest reading", style = MaterialTheme.typography.labelMedium, color = InkFaint)
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("${latest.moisture}% moisture", fontWeight = FontWeight.Bold)
                            Text(
                                "Pump: ${latest.pumpStatus}",
                                color = if (latest.pumpStatus == "ON") Water else InkFaint,
                                fontWeight = FontWeight.Bold,
                            )
                        }
                        MoistureGauge(moisture = latest.moisture)
                        Text(latest.timestamp, style = MaterialTheme.typography.bodySmall, color = InkFaint)
                    }
                }
                LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(snapshot!!.events) { e -> IrrigationRow(e) }
                }
            }
        }
    }
}

@Composable
private fun MoistureGauge(moisture: Double) {
    val fraction = (moisture / 100.0).coerceIn(0.0, 1.0).toFloat()
    val barColor = if (moisture < MOISTURE_THRESHOLD) Urgent else Water

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(10.dp)
            .clip(RoundedCornerShape(100))
            .background(Line),
    ) {
        Box(
            modifier = Modifier
                .fillMaxHeight()
                .fillMaxWidth(fraction)
                .clip(RoundedCornerShape(100))
                .background(barColor),
        )
        // Threshold marker at the pump's ON/OFF cutoff.
        Box(
            modifier = Modifier
                .fillMaxHeight()
                .fillMaxWidth(MOISTURE_THRESHOLD / 100f)
                .padding(start = 0.dp),
            contentAlignment = Alignment.CenterEnd,
        ) {
            Box(
                modifier = Modifier
                    .width(2.dp)
                    .fillMaxHeight()
                    .background(SurfaceAlt),
            )
        }
    }
}

@Composable
fun IrrigationRow(e: IrrigationEvent) {
    Card(
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = SurfaceAlt),
    ) {
        Row(
            Modifier.fillMaxWidth().padding(12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Text("${e.moisture}% - ${e.timestamp}", style = MaterialTheme.typography.bodySmall)
            Text(
                e.pumpStatus,
                style = MaterialTheme.typography.labelMedium,
                color = if (e.pumpStatus == "ON") Water else InkFaint,
            )
        }
    }
}
