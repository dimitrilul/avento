buildscript {
    dependencies {
        // AGP 9 uses built-in Kotlin. Pinning KGP keeps the Compose compiler plugin aligned.
        classpath("org.jetbrains.kotlin:kotlin-gradle-plugin:2.3.21")
    }
}

plugins {
    id("com.android.application") version "9.1.1" apply false
    id("org.jetbrains.kotlin.plugin.compose") version "2.3.21" apply false
}
