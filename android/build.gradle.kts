plugins {
    id("com.android.application") version "9.3.2" apply false
    // AGP 9+ has built-in Kotlin support -- org.jetbrains.kotlin.android is no
    // longer applied separately. The compose compiler plugin still is.
    id("org.jetbrains.kotlin.plugin.compose") version "2.4.10" apply false
}
