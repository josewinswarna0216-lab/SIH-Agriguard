package com.agriguard.app.screens

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.ui.Alignment
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
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.agriguard.app.AppLanguage
import com.agriguard.app.network.ApiClient
import com.agriguard.app.network.LiveResult
import com.agriguard.app.network.MissionPlan
import com.agriguard.app.ui.theme.Beta
import com.agriguard.app.ui.theme.Good
import com.agriguard.app.ui.theme.InkFaint
import com.agriguard.app.ui.theme.Line
import com.agriguard.app.ui.theme.SurfaceAlt
import com.agriguard.app.ui.theme.Urgent
import com.agriguard.app.ui.theme.Water
import kotlinx.coroutines.delay

private const val DESIGN_SIZE = 700f

@Composable
fun MissionPlanScreen() {
    var plan by remember { mutableStateOf<MissionPlan?>(null) }
    var loading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }

    var dronePos by remember { mutableStateOf<Offset?>(null) }
    var phaseText by remember { mutableStateOf("Waiting for the camera device...") }
    var statusText by remember { mutableStateOf("No live activity yet.") }

    // Grid coloring refreshes every few seconds -- new real detections change cell status.
    LaunchedEffect(Unit) {
        while (true) {
            try {
                plan = ApiClient.getMissionPlan()
                error = null
            } catch (e: Exception) {
                error = e.message ?: "Failed to load"
            } finally {
                loading = false
            }
            delay(3000)
        }
    }

    // Drone marker tracks whatever the camera device most recently captured, live --
    // this is a live tracker, not a canned replay.
    LaunchedEffect(Unit) {
        var lastTimestamp: String? = null
        var current = Offset(0f, 0f)
        var basePlaced = false

        suspend fun flyTo(target: Offset) {
            val start = if (basePlaced) current else target
            val steps = 16
            for (i in 1..steps) {
                val t = i / steps.toFloat()
                dronePos = Offset(start.x + (target.x - start.x) * t, start.y + (target.y - start.y) * t)
                delay(20)
            }
            current = target
            basePlaced = true
        }

        while (true) {
            try {
                val live: LiveResult? = ApiClient.getLive()
                val p = plan
                if (live != null && live.timestamp != lastTimestamp) {
                    lastTimestamp = live.timestamp
                    phaseText = "LIVE — TRACKING"
                    val cell = p?.grid?.firstOrNull { it.position.equals(live.position, ignoreCase = true) }
                    if (cell != null) {
                        flyTo(Offset(cell.cx, cell.cy))
                    }
                    val isTa = AppLanguage.current == "ta"
                    val word = if (live.isHealthy) (if (isTa) "ஆரோக்கியமானது" else "Healthy") else (if (isTa) "நோய்" else "DISEASED")
                    val gridNote = if (cell == null) (if (isTa) " (இன்றைய கட்டத்தில் இல்லை)" else " (not on today's grid)") else ""
                    val label = if (isTa) live.labelDisplayTa else live.labelDisplay
                    statusText = "${live.position}$gridNote — $word: $label (${live.confidence}%)"
                }
            } catch (_: Exception) {
                // Transient poll failure -- keep showing the last known state.
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
        Text("Flight Plan", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        Text(
            "Tracks the camera device live -- the marker moves to wherever the latest capture landed. Cells only light up once a position matches \"Row N - Tree M\".",
            color = InkFaint,
            style = MaterialTheme.typography.bodySmall,
        )

        when {
            loading -> CircularProgressIndicator()
            error != null -> Text("Error: $error", color = MaterialTheme.colorScheme.error)
            plan != null -> {
                val p = plan!!
                Canvas(
                    modifier = Modifier
                        .fillMaxWidth()
                        .aspectRatio(1f)
                        .background(SurfaceAlt, RoundedCornerShape(16.dp)),
                ) {
                    val scale = size.width / DESIGN_SIZE
                    fun pt(x: Float, y: Float) = Offset(x * scale, y * scale)

                    drawRect(
                        color = Line,
                        topLeft = pt(60f, 70f),
                        size = Size(560f * scale, 500f * scale),
                        style = Stroke(width = 2f, pathEffect = PathEffect.dashPathEffect(floatArrayOf(3f, 6f))),
                    )

                    val pathPoints = listOf(pt(p.baseX, p.baseY)) + p.grid.map { pt(it.cx, it.cy) }
                    for (i in 0 until pathPoints.size - 1) {
                        drawLine(
                            color = Good,
                            start = pathPoints[i],
                            end = pathPoints[i + 1],
                            strokeWidth = 2f,
                            pathEffect = PathEffect.dashPathEffect(floatArrayOf(1f, 9f)),
                        )
                    }

                    val basePt = pt(p.baseX, p.baseY)
                    drawCircle(color = InkFaint, radius = 14f * scale, center = basePt, style = Stroke(width = 2f))
                    drawCircle(color = InkFaint, radius = 4f * scale, center = basePt)

                    p.grid.forEach { cell ->
                        val center = pt(cell.cx, cell.cy)
                        val r = 11f * scale
                        val (fill, stroke) = when {
                            !cell.visited -> SurfaceAlt to InkFaint
                            cell.isHealthy -> Color(0x331D3324) to Good
                            else -> Color(0x333B1E1A) to Urgent
                        }
                        if (cell.visited && cell.recommendedAction == "extra_orbit") {
                            drawCircle(
                                color = Urgent,
                                radius = r * 2.1f,
                                center = center,
                                style = Stroke(width = 1.8f, pathEffect = PathEffect.dashPathEffect(floatArrayOf(2f, 4f))),
                            )
                        }
                        drawCircle(color = fill, radius = r, center = center)
                        drawCircle(color = stroke, radius = r, center = center, style = Stroke(width = 1.6f))
                    }

                    dronePos?.let { d ->
                        drawCircle(color = Water, radius = 9f * scale, center = pt(d.x, d.y))
                    }
                }

                FlowLegend()

                Text(phaseText, style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.Bold, color = Water)

                Card(
                    shape = RoundedCornerShape(14.dp),
                    colors = CardDefaults.cardColors(containerColor = SurfaceAlt),
                ) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(statusText, style = MaterialTheme.typography.bodyMedium)
                    }
                }
            }
        }
    }
}

private data class LegendItem(val color: Color, val label: String)

@Composable
private fun FlowLegend() {
    val items = listOf(
        LegendItem(Good, "Healthy"),
        LegendItem(Urgent, "Diseased"),
        LegendItem(InkFaint, "Not visited"),
        LegendItem(Urgent, "Flagged for close inspection"),
    )
    LazyRow(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
        items(items) { item ->
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                Canvas(modifier = Modifier.size(9.dp)) {
                    drawCircle(color = item.color, style = Stroke(width = 1.6f))
                }
                Text(item.label, style = MaterialTheme.typography.labelSmall, color = InkFaint)
            }
        }
    }
}
