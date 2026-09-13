package com.agriguard.app.network

data class Detection(
    val timestamp: String,
    val label: String,
    val labelDisplay: String,
    val labelDisplayTa: String,
    val isHealthy: Boolean,
    val confidence: Double,
    val position: String,
    val treatment: String?,
    val treatmentTa: String?,
    val recommendedAction: String,
    val recommendedActionLabel: String,
    val recommendedActionLabelTa: String,
)

data class Summary(
    val totalDetections: Int,
    val healthyCount: Int,
    val diseasedCount: Int,
    val fieldStatus: String,
    val latest: Detection?,
)

data class PositionSummary(
    val position: String,
    val totalVisits: Int,
    val diseasedCount: Int,
    val healthyCount: Int,
    val trend: String,
    val latestLabelDisplay: String,
    val latestLabelDisplayTa: String,
    val latestIsHealthy: Boolean,
    val latestConfidence: Double,
    val latestTimestamp: String,
    val latestTreatment: String?,
    val latestTreatmentTa: String?,
    val recommendedAction: String,
    val recommendedActionLabel: String,
    val recommendedActionLabelTa: String,
)

data class IrrigationEvent(
    val timestamp: String,
    val moisture: Double,
    val pumpStatus: String,
)

data class IrrigationSnapshot(
    val latest: IrrigationEvent?,
    val events: List<IrrigationEvent>,
)

data class MissionCell(
    val position: String,
    val cx: Float,
    val cy: Float,
    val visited: Boolean,
    val isHealthy: Boolean,
    val labelDisplay: String,
    val labelDisplayTa: String,
    val confidence: Double,
    val treatment: String?,
    val treatmentTa: String?,
    val recommendedAction: String,
    val recommendedActionLabel: String,
    val recommendedActionLabelTa: String,
)

data class MissionPlan(
    val grid: List<MissionCell>,
    val baseX: Float,
    val baseY: Float,
)

data class LiveResult(
    val position: String,
    val labelDisplay: String,
    val labelDisplayTa: String,
    val isHealthy: Boolean,
    val confidence: Double,
    val treatment: String?,
    val treatmentTa: String?,
    val recommendedActionLabel: String,
    val recommendedActionLabelTa: String,
    val timestamp: String,
)
