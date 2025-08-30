import org.gradle.kotlin.dsl.implementation // This import might not be strictly necessary with modern syntax

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose) // Make sure this is present for Jetpack Compose
}

android {
    namespace = "com.example.aimessagebot" // From your original file
    compileSdk = 36 // From your original file

    defaultConfig {
        applicationId = "com.example.aimessagebot" // From your original file
        minSdk = 24 // From your original file
        targetSdk = 36 // From your original file
        versionCode = 1 // From your original file
        versionName = "1.0" // From your original file

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_1_8 // Common for Compose
        targetCompatibility = JavaVersion.VERSION_1_8 // Common for Compose
    }
    kotlinOptions {
        jvmTarget = "1.8" // Common for Compose
    }
    buildFeatures {
        compose = true
    }
    composeOptions {
        // IMPORTANT: Use the Kotlin Compiler Extension version compatible with your libs.versions.toml composeBom
        // Check the official Compose release notes for the correct version mapping.
        // For composeBom = "2024.09.00" and Kotlin 2.0.21, you'll need a recent version.
        // As an example, for Compose 1.6.x and Kotlin 1.9.22, it was "1.5.8".
        // This will be different for your newer versions.
        kotlinCompilerExtensionVersion = libs.versions.kotlinCompilerExtension.get() // Assuming you add this to your TOML
    }
}

dependencies {
    // Import the Compose BOM (Bill of Materials)
    // This will manage the versions of your Compose libraries
    implementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(platform(libs.androidx.compose.bom))

    // Core AndroidX libraries (using aliases from libs.versions.toml)
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.activity.compose)

    // Jetpack Compose UI libraries (versions managed by BOM)
    implementation(libs.androidx.ui)
    implementation(libs.androidx.ui.graphics)
    implementation(libs.androidx.ui.tooling.preview)
    implementation(libs.androidx.material3)

    // Other libraries (using aliases from libs.versions.toml)
    implementation(libs.okhttp)
    implementation(libs.kotlinx.coroutines.android)

    // Test dependencies (using aliases from libs.versions.toml)
    testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(libs.androidx.ui.test.junit4) // For Compose UI tests

    // Debug dependencies (using aliases from libs.versions.toml)
    debugImplementation(libs.androidx.ui.tooling)
    debugImplementation(libs.androidx.ui.test.manifest)
}
