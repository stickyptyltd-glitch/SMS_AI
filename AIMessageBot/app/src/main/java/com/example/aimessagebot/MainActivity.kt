// MainActivity.kt
package com.example.aimessagebot

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.provider.Settings
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.text.input.PasswordVisualTransformation
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {

    private val notificationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) {
            Log.d("MessageBot", "Notification permission granted")
        } else {
            Log.d("MessageBot", "Notification permission denied")
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Enable debug logging
        Log.d("MessageBot", "App started - MainActivity created")

        setContent {
            MaterialTheme {
                MainScreen(
                    onRequestPermissions = ::requestPermissions,
                    onOpenNotificationAccess = ::openNotificationAccessSettings,
                    onTestMessageProcessing = ::testMessageProcessing,
                    onTestAIResponse = ::testAIResponseGeneration
                )
            }
        }
    }

    private fun requestPermissions() {
        Log.d("MessageBot", "Requesting notification permissions")
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
            != PackageManager.PERMISSION_GRANTED) {
            notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
        } else {
            Log.d("MessageBot", "Notification permission already granted")
        }
    }

    private fun openNotificationAccessSettings() {
        Log.d("MessageBot", "Opening notification access settings")
        val intent = Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)
        startActivity(intent)
    }

    private fun testMessageProcessing() {
        Log.d("MessageBot", "=== TESTING MESSAGE PROCESSING ===")

        try {
            // Create test message
            val testMessage = MessageData(
                sender = "Test User",
                message = "Hello, how are you today?",
                timestamp = System.currentTimeMillis(),
                packageName = "com.whatsapp"
            )

            Log.d("MessageBot", "Test message created: ${testMessage.message}")
            Log.d("MessageBot", "From: ${testMessage.sender}")

            // Test speech analysis
            val analyzer = SpeechPatternAnalyzer()
            val profile = analyzer.analyzeSender("TestUser", testMessage.message)

            Log.d("MessageBot", "Speech analysis complete:")
            Log.d("MessageBot", "- Communication style: ${profile.communicationStyle}")
            Log.d("MessageBot", "- Preferred length: ${profile.preferredLength}")
            Log.d("MessageBot", "- Emotional patterns: ${profile.emotionalPatterns}")

            Log.d("MessageBot", "=== MESSAGE PROCESSING TEST COMPLETED ===")

        } catch (e: Exception) {
            Log.e("MessageBot", "Error during message processing test: ${e.message}", e)
        }
    }

    private fun testAIResponseGeneration() {
        Log.d("MessageBot", "=== TESTING AI RESPONSE GENERATION ===")

        CoroutineScope(Dispatchers.IO).launch {
            try {
                val processor = AIMessageProcessor()

                // Create test profile
                val testProfile = SenderProfile(
                    senderId = "TestUser",
                    communicationStyle = "casual",
                    avgResponseTime = 5000L,
                    preferredLength = "short",
                    emotionalPatterns = listOf("friendly"),
                    messageCount = 1
                )

                Log.d("MessageBot", "Testing with message: 'Hey, what's up?'")
                Log.d("MessageBot", "Sender profile: ${testProfile.communicationStyle}")

                // Generate response (this will use mock response for now)
                val response = processor.generateResponse(
                    message = "Hey, what's up?",
                    senderProfile = testProfile,
                    instructions = "Reply casually and briefly"
                )

                Log.d("MessageBot", "AI Response generated: $response")
                Log.d("MessageBot", "=== AI RESPONSE TEST COMPLETED ===")

            } catch (e: Exception) {
                Log.e("MessageBot", "Error testing AI response: ${e.message}", e)
            }
        }
    }
}

@Composable
fun MainScreen(
    onRequestPermissions: () -> Unit,
    onOpenNotificationAccess: () -> Unit,
    onTestMessageProcessing: () -> Unit,
    onTestAIResponse: () -> Unit
) {
    var apiKey by remember { mutableStateOf("") }
    var instructions by remember { mutableStateOf("Reply professionally and briefly") }
    var isServiceEnabled by remember { mutableStateOf(false) }
    var testResult by remember { mutableStateOf("") }
    var useOpenAI by remember { mutableStateOf(false) }
    var serverUrl by remember { mutableStateOf("http://192.168.1.107:8081") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(8.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Text(
            text = "AI Message Bot",
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold
        )

        Card(
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(
                modifier = Modifier.padding(12.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                Text(
                    text = "Setup Required",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )

                Button(
                    onClick = onRequestPermissions,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Grant Notification Permission")
                }

                Button(
                    onClick = onOpenNotificationAccess,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Enable Notification Access")
                }
            }
        }

        // Testing Section
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.secondaryContainer
            )
        ) {
            Column(
                modifier = Modifier.padding(12.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                Text(
                    text = "Testing Tools",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )

                Text(
                    text = "Use these buttons to test app functionality. Check Logcat for results.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSecondaryContainer.copy(alpha = 0.7f)
                )

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Button(
                        onClick = {
                            onTestMessageProcessing()
                            testResult = "Message processing test started - check Logcat for results"
                        },
                        modifier = Modifier.weight(1f)
                    ) {
                        Text("Test Analysis", maxLines = 1)
                    }

                    Button(
                        onClick = {
                            onTestAIResponse()
                            testResult = "AI response test started - check Logcat for results"
                        },
                        modifier = Modifier.weight(1f)
                    ) {
                        Text("Test AI", maxLines = 1)
                    }
                }

                if (testResult.isNotEmpty()) {
                    Text(
                        text = testResult,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.padding(top = 8.dp)
                    )
                }
            }
        }

        OutlinedTextField(
            value = serverUrl,
            onValueChange = { serverUrl = it },
            label = { Text("Server URL") },
            placeholder = { Text("http://192.168.1.107:8081") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )

        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Checkbox(
                checked = useOpenAI,
                onCheckedChange = { useOpenAI = it }
            )
            Text("Use ChatGPT (OpenAI) - Better responses!")
        }

        if (useOpenAI) {
            OutlinedTextField(
                value = apiKey,
                onValueChange = { apiKey = it },
                label = { Text("OpenAI API Key") },
                placeholder = { Text("sk-...") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                visualTransformation = PasswordVisualTransformation()
            )
        }

        OutlinedTextField(
            value = instructions,
            onValueChange = { instructions = it },
            label = { Text("Reply Instructions") },
            placeholder = { Text("e.g., 'Reply professionally and briefly'") },
            modifier = Modifier.fillMaxWidth(),
            minLines = 3
        )

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text("Auto-Reply Service")
            Switch(
                checked = isServiceEnabled,
                onCheckedChange = {
                    isServiceEnabled = it
                    Log.d("MessageBot", "Auto-reply service ${if (it) "enabled" else "disabled"}")
                }
            )
        }

        if (isServiceEnabled) {
            Card(
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.primaryContainer
                )
            ) {
                Column(
                    modifier = Modifier.padding(16.dp)
                ) {
                    Text(
                        text = "✅ Service is running",
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.primary
                    )
                    Text(
                        text = "Messages will be analyzed and replied to automatically. Check Logcat for activity.",
                        style = MaterialTheme.typography.bodySmall,
                        modifier = Modifier.padding(top = 4.dp)
                    )
                }
            }
        }

        // Debug info card
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surfaceVariant
            )
        ) {
            Column(
                modifier = Modifier.padding(16.dp)
            ) {
                Text(
                    text = "🔍 Debug Info",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = "• Open Logcat in Android Studio\n• Filter by 'MessageBot'\n• Send test message or use test buttons\n• Look for processing logs",
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.padding(top = 4.dp)
                )
            }
        }
    }
}