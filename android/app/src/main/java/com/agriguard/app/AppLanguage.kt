package com.agriguard.app

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue

/** "en" or "ta" -- read inside composables to pick which text field to show. */
object AppLanguage {
    var current by mutableStateOf("en")

    fun toggle() {
        current = if (current == "en") "ta" else "en"
    }
}
