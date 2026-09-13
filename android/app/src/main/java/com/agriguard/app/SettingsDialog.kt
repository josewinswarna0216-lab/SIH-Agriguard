package com.agriguard.app

import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import com.agriguard.app.network.ServerConfig

@Composable
fun SettingsDialog(onDismiss: () -> Unit) {
    val context = LocalContext.current
    var urlInput by remember { mutableStateOf(ServerConfig.baseUrl) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Server Address") },
        text = {
            OutlinedTextField(
                value = urlInput,
                onValueChange = { urlInput = it },
                label = { Text("http://<mac-ip>:5001") },
                singleLine = true,
            )
        },
        confirmButton = {
            Button(onClick = {
                ServerConfig.save(context, urlInput.trim().trimEnd('/'))
                onDismiss()
            }) { Text("Save") }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Cancel") }
        },
    )
}
