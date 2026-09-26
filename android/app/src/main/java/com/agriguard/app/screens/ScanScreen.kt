package com.agriguard.app.screens

import android.graphics.Bitmap
import android.graphics.ImageDecoder
import android.net.Uri
import android.os.Build
import android.provider.MediaStore
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.PhotoLibrary
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.agriguard.app.AppLanguage
import com.agriguard.app.ml.OnDeviceClassifier
import com.agriguard.app.ml.SUPPORTED_CROPS
import com.agriguard.app.ml.labelFor
import com.agriguard.app.ml.treatmentFor
import com.agriguard.app.ui.theme.InkFaint
import com.agriguard.app.ui.theme.Line
import com.agriguard.app.ui.theme.SurfaceAlt
import com.agriguard.app.ui.theme.Urgent
import com.agriguard.app.ui.theme.UrgentSoft
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * Offline leaf scan.
 *
 * Nothing on this screen touches the network -- the model, the labels and the
 * treatment advice all ship inside the APK. That is the point: put the phone in
 * airplane mode and this screen behaves identically, which is what the problem
 * statement means by real-time on-device intelligence in areas with limited
 * connectivity. Results can be synced to the server later, but a farmer never
 * waits on a tunnel to find out what is wrong with their crop.
 */
@Composable
fun ScanScreen() {
    val context = LocalContext.current
    val classifier = remember { OnDeviceClassifier(context) }
    DisposableEffect(Unit) { onDispose { classifier.close() } }

    var crop by remember { mutableStateOf(SUPPORTED_CROPS.first()) }
    var bitmap by remember { mutableStateOf<Bitmap?>(null) }
    var result by remember { mutableStateOf<OnDeviceClassifier.Result?>(null) }
    var running by remember { mutableStateOf(false) }

    val cameraLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.TakePicturePreview(),
    ) { captured -> if (captured != null) { bitmap = captured; result = null } }

    val galleryLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.GetContent(),
    ) { uri -> if (uri != null) { bitmap = decodeBitmap(context, uri); result = null } }

    // Re-run whenever a new photo arrives or the farmer corrects the crop --
    // picking the right crop is itself a meaningful accuracy change, so it
    // should not need a second button press.
    LaunchedEffect(bitmap, crop) {
        val source = bitmap ?: return@LaunchedEffect
        running = true
        result = withContext(Dispatchers.Default) { classifier.classify(source, crop) }
        running = false
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(
            if (AppLanguage.current == "ta") "பயிரைத் தேர்ந்தெடுக்கவும்" else "Select your crop",
            style = MaterialTheme.typography.labelLarge,
            color = InkFaint,
        )
        LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            items(SUPPORTED_CROPS) { option ->
                FilterChip(
                    selected = option == crop,
                    onClick = { crop = option },
                    label = { Text(option) },
                    colors = FilterChipDefaults.filterChipColors(),
                )
            }
        }

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
            Button(onClick = { cameraLauncher.launch(null) }, modifier = Modifier.weight(1f)) {
                Icon(Icons.Filled.CameraAlt, contentDescription = null)
                Text("  " + if (AppLanguage.current == "ta") "படம் எடு" else "Camera")
            }
            OutlinedButton(onClick = { galleryLauncher.launch("image/*") }, modifier = Modifier.weight(1f)) {
                Icon(Icons.Filled.PhotoLibrary, contentDescription = null)
                Text("  " + if (AppLanguage.current == "ta") "படம் தேர்வு" else "Gallery")
            }
        }

        bitmap?.let { preview ->
            Image(
                bitmap = preview.asImageBitmap(),
                contentDescription = null,
                contentScale = ContentScale.Crop,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(220.dp)
                    .clip(RoundedCornerShape(12.dp)),
            )
        }

        when {
            running -> Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.Center,
            ) { CircularProgressIndicator() }

            result != null -> ResultCard(result!!)

            else -> Text(
                if (AppLanguage.current == "ta") {
                    "இலையின் படத்தை எடுத்தால் இணையம் இல்லாமல் நோய் கண்டறியப்படும்."
                } else {
                    "Photograph a leaf. Diagnosis runs on this phone — no internet needed."
                },
                style = MaterialTheme.typography.bodyMedium,
                color = InkFaint,
            )
        }
    }
}

@Composable
private fun ResultCard(result: OnDeviceClassifier.Result) {
    val lang = AppLanguage.current

    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = SurfaceAlt),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            if (result.uncertain) {
                // Deliberately refuses to name a disease. A confident wrong
                // answer costs the farmer a spray; "retake the photo" costs
                // them ten seconds.
                Text(
                    if (lang == "ta") "உறுதியாக தெரியவில்லை" else "NOT SURE",
                    color = Urgent,
                    style = MaterialTheme.typography.labelSmall,
                    modifier = Modifier
                        .background(UrgentSoft, RoundedCornerShape(100))
                        .padding(horizontal = 10.dp, vertical = 4.dp),
                )
                Text(
                    if (lang == "ta") {
                        "தெளிவான ஒற்றை இலையை, நல்ல வெளிச்சத்தில் மீண்டும் படம் எடுக்கவும்."
                    } else {
                        "Retake in better light with a single leaf filling the frame."
                    },
                    style = MaterialTheme.typography.bodyMedium,
                )
                Text(
                    (if (lang == "ta") "மிக அருகில்: " else "Closest match: ") +
                        labelFor(result.className, lang) +
                        " (${(result.confidence * 100).toInt()}%)",
                    style = MaterialTheme.typography.bodySmall,
                    color = InkFaint,
                )
            } else {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    HealthPill(result.healthy)
                    Text(
                        "${(result.confidence * 100).toInt()}%",
                        style = MaterialTheme.typography.labelLarge,
                        color = InkFaint,
                    )
                }
                Text(
                    labelFor(result.className, lang),
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                )
                Text(
                    treatmentFor(result.className, lang),
                    style = MaterialTheme.typography.bodyMedium,
                )
            }

            // The latency number is here on purpose: it is the evidence that
            // this ran locally, and it is the figure to compare against once
            // the model is dispatched to the Snapdragon NPU.
            Text(
                "⚡ ${result.inferenceMs} ms · " +
                    if (lang == "ta") "இந்த தொலைபேசியில் — இணையம் இல்லை" else "on this phone · no network used",
                style = MaterialTheme.typography.bodySmall,
                color = InkFaint,
                modifier = Modifier
                    .background(Line, RoundedCornerShape(6.dp))
                    .padding(horizontal = 8.dp, vertical = 4.dp),
            )
        }
    }
}

/**
 * ImageDecoder hands back a HARDWARE bitmap by default, which has no backing
 * pixel array -- getPixels() on it throws. Force a software allocation so the
 * classifier can read it.
 */
private fun decodeBitmap(context: android.content.Context, uri: Uri): Bitmap? = try {
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
        ImageDecoder.decodeBitmap(ImageDecoder.createSource(context.contentResolver, uri)) { decoder, _, _ ->
            decoder.allocator = ImageDecoder.ALLOCATOR_SOFTWARE
            decoder.isMutableRequired = false
        }
    } else {
        @Suppress("DEPRECATION")
        MediaStore.Images.Media.getBitmap(context.contentResolver, uri)
    }
} catch (e: Exception) {
    null
}
