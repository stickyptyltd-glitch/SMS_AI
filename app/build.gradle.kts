plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    // Google Play Publisher (CI publishing)
    id("com.github.triplet.play") version "3.8.6"
}

android {
    namespace = "au.st1cky.smsautoframe"
    compileSdk = 35

    defaultConfig {
        applicationId = "au.st1cky.smsautoframe"
        minSdk = 26
        targetSdk = 35
        versionCode = 101
        versionName = "1.0.1"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }
    flavorDimensions += listOf("dist")
    productFlavors {
        create("store") { dimension = "dist" }
        create("full") { dimension = "dist" }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
        debug {
            isMinifyEnabled = false
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }

    // Signing (reference snippet; configure via Android Studio or uncomment and set gradle.properties)
    // signingConfigs {
    //     create("release") {
    //         val storeFileProp = providers.gradleProperty("DAYLE_STORE_FILE").orNull
    //         if (storeFileProp != null) {
    //             storeFile = file(storeFileProp)
    //             storePassword = providers.gradleProperty("DAYLE_STORE_PASSWORD").orNull
    //             keyAlias = providers.gradleProperty("DAYLE_KEY_ALIAS").orNull ?: "dayle"
    //             keyPassword = providers.gradleProperty("DAYLE_KEY_PASSWORD").orNull
    //         }
    //     }
    // }
    // buildTypes {
    //     release { if (signingConfigs.names.contains("release")) signingConfig = signingConfigs.getByName("release") }
    // }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")

    // Networking
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")

    // Lifecycle
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.4")
    implementation("androidx.activity:activity-ktx:1.9.1")

    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")

    // Foreground service notification compat
    implementation("androidx.core:core-ktx:1.13.1")

    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.6.1")
}
// Minimal Play Publisher defaults (credentials/track passed via -P flags in CI)
play {
    defaultToAppBundles.set(true)
}
