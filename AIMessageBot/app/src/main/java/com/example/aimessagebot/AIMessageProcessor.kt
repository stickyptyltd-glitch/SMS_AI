package com.example.aimessagebot

import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject

class AIMessageProcessor {
    private val client = OkHttpClient()
    private val JSON = "application/json; charset=utf-8".toMediaType()

    suspend fun generateResponse(
        message: String,
        senderProfile: SenderProfile,
        instructions: String
    ): String = withContext(Dispatchers.IO) {

        Log.d("MessageBot", "Generating AI response for message: $message")

        // FOR TESTING: Return a mock response first
        // Comment this out when you want to use real API
        val mockResponse = generateMockResponse(message, senderProfile)
        Log.d("MessageBot", "Mock response generated: $mockResponse")
        return@withContext mockResponse

        // UNCOMMENT BELOW FOR REAL API USAGE:
        /*
        val systemPrompt = buildSystemPrompt(instructions, senderProfile)
        return@withContext callChatGPT(systemPrompt, message)
        */
    }

    // Mock response for testing (no API needed)
    private fun generateMockResponse(message: String, profile: SenderProfile): String {
        Log.d("MessageBot", "Using mock response based on profile: ${profile.communicationStyle}")

        return when (profile.communicationStyle.lowercase()) {
            "professional" -> "Thank you for your message. I'll get back to you shortly."
            "casual" -> "Hey! Thanks for reaching out. I'll reply soon!"
            "concise" -> "Got it, thanks!"
            "expressive" -> "Thanks so much for your message! I really appreciate it! 😊"
            else -> "Thanks for your message! I'll get back to you soon."
        }
    }

    private fun buildSystemPrompt(instructions: String, profile: SenderProfile): String {
        return """
            $instructions
            
            Sender Analysis:
            - Communication style: ${profile.communicationStyle}
            - Typical response time: ${profile.avgResponseTime}ms
            - Preferred message length: ${profile.preferredLength}
            - Emotional tone patterns: ${profile.emotionalPatterns.joinToString(", ")}
            
            Adapt your response to match their communication preferences while following the main instructions.
        """.trimIndent()
    }

    private suspend fun callChatGPT(systemPrompt: String, userMessage: String): String {
        val apiKey = getStoredApiKey()

        if (apiKey.isBlank() || apiKey == "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") {
            Log.w("MessageBot", "No API key configured, using mock response")
            return "Please configure your OpenAI API key to use real AI responses."
        }

        val requestBody = JSONObject().apply {
            put("model", "gpt-3.5-turbo")
            put("messages", JSONArray().apply {
                put(JSONObject().apply {
                    put("role", "system")
                    put("content", systemPrompt)
                })
                put(JSONObject().apply {
                    put("role", "user")
                    put("content", userMessage)
                })
            })
            put("max_tokens", 150)
            put("temperature", 0.7)
        }

        val request = Request.Builder()
            .url("https://api.openai.com/v1/chat/completions")
            .header("Authorization", "Bearer $apiKey")
            .header("Content-Type", "application/json")
            .post(requestBody.toString().toRequestBody(JSON))
            .build()

        return try {
            Log.d("MessageBot", "Calling ChatGPT API...")
            val response = client.newCall(request).execute()
            val responseBody = response.body?.string()

            if (!response.isSuccessful) {
                Log.e("MessageBot", "API call failed: ${response.code} - $responseBody")
                return "Sorry, I couldn't process your message right now."
            }

            val jsonResponse = JSONObject(responseBody ?: "")
            val aiResponse = jsonResponse
                .getJSONArray("choices")
                .getJSONObject(0)
                .getJSONObject("message")
                .getString("content")
                .trim()

            Log.d("MessageBot", "ChatGPT response received: $aiResponse")
            return aiResponse

        } catch (e: Exception) {
            Log.e("MessageBot", "Error calling ChatGPT API", e)
            return "Sorry, I couldn't process your message right now."
        }
    }

    private fun getStoredApiKey(): String {
        // TODO: Retrieve API key from secure storage or SharedPreferences
        // For now, return placeholder
        return "your-api-key-here"
    }
}