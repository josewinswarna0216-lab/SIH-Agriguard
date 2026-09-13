package com.agriguard.app.network

import android.content.Context
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

private const val PREFS_NAME = "agriguard_settings"
private const val KEY_BASE_URL = "base_url"
private const val DEFAULT_BASE_URL = "http://192.168.0.3:5001"

/**
 * The Flask dev server's address. Editable at runtime from the app's
 * Settings dialog (top bar gear icon) and persisted across restarts --
 * the dev machine's IP can change between WiFi networks or reconnects, and
 * there's no way to predict the venue's network on presentation day, so
 * this must be changeable without a rebuild.
 */
object ServerConfig {
    var baseUrl by mutableStateOf(DEFAULT_BASE_URL)

    fun load(context: Context) {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        baseUrl = prefs.getString(KEY_BASE_URL, DEFAULT_BASE_URL) ?: DEFAULT_BASE_URL
    }

    fun save(context: Context, url: String) {
        baseUrl = url
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_BASE_URL, url)
            .apply()
    }
}

object ApiClient {
    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .writeTimeout(15, TimeUnit.SECONDS)
        .build()

    suspend fun predictV2(imageBytes: ByteArray, position: String): Detection =
        withContext(Dispatchers.IO) {
            val body = MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("position", position)
                .addFormDataPart(
                    "image", "capture.jpg",
                    imageBytes.toRequestBody("image/jpeg".toMediaType()),
                )
                .build()
            val request = Request.Builder()
                .url("${ServerConfig.baseUrl}/predict-v2")
                .post(body)
                .build()
            val json = execute(request)
            parseDetection(json)
        }

    suspend fun getLive(): LiveResult? = withContext(Dispatchers.IO) {
        val request = Request.Builder().url("${ServerConfig.baseUrl}/live-data-v2").get().build()
        val json = execute(request)
        if (!json.has("timestamp")) return@withContext null
        LiveResult(
            position = json.getString("position"),
            labelDisplay = json.getString("label_display"),
            labelDisplayTa = json.getString("label_display_ta"),
            isHealthy = json.getBoolean("is_healthy"),
            confidence = json.getDouble("confidence"),
            treatment = json.optStringOrNull("treatment"),
            treatmentTa = json.optStringOrNull("treatment_ta"),
            recommendedActionLabel = json.getString("recommended_action_label"),
            recommendedActionLabelTa = json.getString("recommended_action_label_ta"),
            timestamp = json.getString("timestamp"),
        )
    }

    fun frameImageUrl(cacheBuster: Long): String = "${ServerConfig.baseUrl}/static/last_frame_v2.jpg?t=$cacheBuster"

    fun voiceReportUrl(lang: String): String = "${ServerConfig.baseUrl}/voice-report-v2/$lang"

    suspend fun getDetections(): List<Detection> = withContext(Dispatchers.IO) {
        val request = Request.Builder().url("${ServerConfig.baseUrl}/api/v2/detections").get().build()
        val array = JSONArray(executeRaw(request))
        (0 until array.length()).map { parseDetection(array.getJSONObject(it)) }
    }

    suspend fun getSummary(): Summary = withContext(Dispatchers.IO) {
        val request = Request.Builder().url("${ServerConfig.baseUrl}/api/v2/summary").get().build()
        val json = execute(request)
        Summary(
            totalDetections = json.getInt("total_detections"),
            healthyCount = json.getInt("healthy_count"),
            diseasedCount = json.getInt("diseased_count"),
            fieldStatus = json.getString("field_status"),
            latest = json.optJSONObject("latest")?.let { parseDetection(it) },
        )
    }

    suspend fun getPositions(): List<PositionSummary> = withContext(Dispatchers.IO) {
        val request = Request.Builder().url("${ServerConfig.baseUrl}/api/v2/positions").get().build()
        val array = JSONArray(executeRaw(request))
        (0 until array.length()).map { i ->
            val json = array.getJSONObject(i)
            PositionSummary(
                position = json.getString("position"),
                totalVisits = json.getInt("total_visits"),
                diseasedCount = json.getInt("diseased_count"),
                healthyCount = json.getInt("healthy_count"),
                trend = json.getString("trend"),
                latestLabelDisplay = json.getString("latest_label_display"),
                latestLabelDisplayTa = json.getString("latest_label_display_ta"),
                latestIsHealthy = json.getBoolean("latest_is_healthy"),
                latestConfidence = json.getDouble("latest_confidence"),
                latestTimestamp = json.getString("latest_timestamp"),
                latestTreatment = json.optStringOrNull("latest_treatment"),
                latestTreatmentTa = json.optStringOrNull("latest_treatment_ta"),
                recommendedAction = json.getString("recommended_action"),
                recommendedActionLabel = json.getString("recommended_action_label"),
                recommendedActionLabelTa = json.getString("recommended_action_label_ta"),
            )
        }
    }

    suspend fun getMissionPlan(): MissionPlan = withContext(Dispatchers.IO) {
        val request = Request.Builder().url("${ServerConfig.baseUrl}/api/v2/mission-plan").get().build()
        val json = execute(request)
        val gridArray = json.getJSONArray("grid")
        val base = json.getJSONObject("base")
        val grid = (0 until gridArray.length()).map { i ->
            val cell = gridArray.getJSONObject(i)
            val visited = cell.getBoolean("visited")
            MissionCell(
                position = cell.getString("position"),
                cx = cell.getDouble("cx").toFloat(),
                cy = cell.getDouble("cy").toFloat(),
                visited = visited,
                isHealthy = if (visited) cell.getBoolean("is_healthy") else true,
                labelDisplay = if (visited) cell.getString("label_display") else "",
                labelDisplayTa = if (visited) cell.getString("label_display_ta") else "",
                confidence = if (visited) cell.getDouble("confidence") else 0.0,
                treatment = if (visited) cell.optStringOrNull("treatment") else null,
                treatmentTa = if (visited) cell.optStringOrNull("treatment_ta") else null,
                recommendedAction = if (visited) cell.getString("recommended_action") else "",
                recommendedActionLabel = if (visited) cell.getString("recommended_action_label") else "",
                recommendedActionLabelTa = if (visited) cell.getString("recommended_action_label_ta") else "",
            )
        }
        MissionPlan(
            grid = grid,
            baseX = base.getDouble("x").toFloat(),
            baseY = base.getDouble("y").toFloat(),
        )
    }

    suspend fun getIrrigation(): IrrigationSnapshot = withContext(Dispatchers.IO) {
        val request = Request.Builder().url("${ServerConfig.baseUrl}/api/irrigation").get().build()
        val json = execute(request)
        val events = json.getJSONArray("events")
        IrrigationSnapshot(
            latest = json.optJSONObject("latest")?.let { parseIrrigationEvent(it) },
            events = (0 until events.length()).map { parseIrrigationEvent(events.getJSONObject(it)) },
        )
    }

    private fun parseDetection(json: JSONObject) = Detection(
        timestamp = json.getString("timestamp"),
        label = json.getString("label"),
        labelDisplay = json.getString("label_display"),
        labelDisplayTa = json.getString("label_display_ta"),
        isHealthy = json.getBoolean("is_healthy"),
        confidence = json.getDouble("confidence"),
        position = json.getString("position"),
        treatment = json.optStringOrNull("treatment"),
        treatmentTa = json.optStringOrNull("treatment_ta"),
        recommendedAction = json.getString("recommended_action"),
        recommendedActionLabel = json.getString("recommended_action_label"),
        recommendedActionLabelTa = json.getString("recommended_action_label_ta"),
    )

    private fun parseIrrigationEvent(json: JSONObject) = IrrigationEvent(
        timestamp = json.getString("timestamp"),
        moisture = json.getDouble("moisture"),
        pumpStatus = json.getString("pump_status"),
    )

    private fun JSONObject.optStringOrNull(key: String): String? =
        if (isNull(key) || !has(key)) null else getString(key)

    private fun execute(request: Request): JSONObject = JSONObject(executeRaw(request))

    private fun executeRaw(request: Request): String {
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                throw ApiException("Server returned ${response.code}")
            }
            return response.body?.string() ?: throw ApiException("Empty response body")
        }
    }
}

class ApiException(message: String) : Exception(message)
