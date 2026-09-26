package com.agriguard.app.ml

import android.content.Context
import android.graphics.Bitmap
import android.os.SystemClock
import org.tensorflow.lite.Interpreter
import java.io.FileInputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.MappedByteBuffer
import java.nio.channels.FileChannel

/**
 * Runs the crop-disease model on the phone itself.
 *
 * The whole point of this class is that it makes no network call. The server
 * (and its ngrok tunnel) is now an optional sync target, not a dependency --
 * which is what "field-deployable, real-time on-device intelligence" in the
 * problem statement actually requires. If the phone is in airplane mode in the
 * middle of a field, everything below still works.
 *
 * Upgrade path worth knowing about: this uses the stock CPU interpreter, which
 * runs everywhere. On a Snapdragon device the same .tflite can be dispatched to
 * the NPU via the LiteRT QNN accelerator for a large latency and power win --
 * [Result.inferenceMs] is reported so that comparison can be measured rather
 * than claimed.
 */
class OnDeviceClassifier(context: Context) {

    /**
     * One classification. [uncertain] matters as much as [className]: a model
     * asked about a photo of a hand will still return a crop disease with high
     * confidence unless something refuses to answer, so we refuse here rather
     * than showing the farmer a confident wrong diagnosis.
     */
    data class Result(
        val className: String,
        val confidence: Float,
        val healthy: Boolean,
        val uncertain: Boolean,
        val runnerUp: String?,
        val runnerUpConfidence: Float,
        val inferenceMs: Long,
    )

    private val interpreter: Interpreter = Interpreter(
        loadModel(context, MODEL_ASSET),
        Interpreter.Options().apply { setNumThreads(4) },
    )

    // Reused across calls -- allocating a 300KB direct buffer per frame is the
    // kind of thing that shows up as jank when scanning several leaves in a row.
    private val inputBuffer: ByteBuffer =
        ByteBuffer.allocateDirect(INPUT_SIZE * INPUT_SIZE * 3 * 4).order(ByteOrder.nativeOrder())
    private val outputBuffer = Array(1) { FloatArray(CLASS_NAMES_V2.size) }
    private val pixels = IntArray(INPUT_SIZE * INPUT_SIZE)

    /**
     * Classify [bitmap] as [crop]. Naming the crop is not just UI convenience:
     * it masks the output down to that crop's classes before picking a winner,
     * so a mango photo can never come back as a sugarcane disease. Pass null to
     * let all 34 classes compete.
     */
    @Synchronized
    fun classify(bitmap: Bitmap, crop: String?): Result {
        fillInput(bitmap)

        val start = SystemClock.elapsedRealtime()
        interpreter.run(inputBuffer, outputBuffer)
        val elapsed = SystemClock.elapsedRealtime() - start

        val raw = outputBuffer[0]
        val candidates = crop?.let { CROP_CLASS_INDICES[it] } ?: raw.indices.toList()
        val probabilities = renormalise(raw, candidates)

        val ranked = candidates.indices.sortedByDescending { probabilities[it] }
        val topIdx = candidates[ranked[0]]
        val topProb = probabilities[ranked[0]]
        val secondIdx = ranked.getOrNull(1)?.let { candidates[it] }
        val secondProb = ranked.getOrNull(1)?.let { probabilities[it] } ?: 0f

        // Two independent reasons to decline to answer. A low absolute score
        // means the image does not look like anything the model knows. A narrow
        // margin means it cannot separate two diseases -- telling the farmer to
        // spray for the wrong one is worse than telling them to retake a photo.
        val uncertain = topProb < MIN_CONFIDENCE || (topProb - secondProb) < MIN_MARGIN

        return Result(
            className = CLASS_NAMES_V2[topIdx],
            confidence = topProb,
            healthy = isHealthy(CLASS_NAMES_V2[topIdx]),
            uncertain = uncertain,
            runnerUp = secondIdx?.let { CLASS_NAMES_V2[it] },
            runnerUpConfidence = secondProb,
            inferenceMs = elapsed,
        )
    }

    fun close() = interpreter.close()

    /**
     * Must stay equivalent to `preprocess_v2` in server/app.py.
     *
     * Two details here are counter-intuitive and both were already paid for on
     * the server side:
     *
     * 1. This is a plain stretch to 160x160, NOT the letterbox-with-black-pad
     *    that the older 38-class model uses. This model was trained through
     *    `image_dataset_from_directory`, which stretches without preserving
     *    aspect ratio -- feeding it a padded image gives near-random confidence
     *    on images it should nail.
     * 2. There is no /255. The model carries its own Rescaling layer, so
     *    normalising here would divide twice.
     */
    private fun fillInput(bitmap: Bitmap) {
        val scaled = Bitmap.createScaledBitmap(bitmap, INPUT_SIZE, INPUT_SIZE, true)

        scaled.getPixels(pixels, 0, INPUT_SIZE, 0, 0, INPUT_SIZE, INPUT_SIZE)
        inputBuffer.rewind()
        for (pixel in pixels) {
            inputBuffer.putFloat(((pixel shr 16) and 0xFF).toFloat())
            inputBuffer.putFloat(((pixel shr 8) and 0xFF).toFloat())
            inputBuffer.putFloat((pixel and 0xFF).toFloat())
        }
        inputBuffer.rewind()

        if (scaled !== bitmap) scaled.recycle()
    }

    /**
     * The model's own output layer is already a softmax -- its raw output sums
     * to ~1.0. Running softmax over it again is not a no-op: it flattens a
     * genuine 100% into single digits. So we only mask down to the chosen
     * crop's classes and renormalise over what is left, exactly as
     * `predict_v2` does.
     */
    private fun renormalise(raw: FloatArray, candidates: List<Int>): FloatArray {
        var total = 0f
        for (index in candidates) total += raw[index]
        return FloatArray(candidates.size) {
            if (total > 0f) raw[candidates[it]] / total else 0f
        }
    }

    private fun loadModel(context: Context, asset: String): MappedByteBuffer {
        context.assets.openFd(asset).use { fd ->
            FileInputStream(fd.fileDescriptor).use { stream ->
                return stream.channel.map(
                    FileChannel.MapMode.READ_ONLY,
                    fd.startOffset,
                    fd.declaredLength,
                )
            }
        }
    }

    companion object {
        private const val MODEL_ASSET = "plant_disease_model_multicrop.tflite"
        private const val INPUT_SIZE = 160

        /** Below this, we say "not sure" instead of naming a disease. */
        const val MIN_CONFIDENCE = 0.55f

        /** Top-1 must beat top-2 by at least this much to count as a decision. */
        const val MIN_MARGIN = 0.15f
    }
}
