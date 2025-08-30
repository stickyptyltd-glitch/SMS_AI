// MessageData.kt - Keep this file exactly like this
package com.example.aimessagebot

data class MessageData(
    val sender: String,
    val message: String,
    val timestamp: Long,
    val packageName: String
)

data class MessageAnalysis(
    val wordCount: Int,
    val sentenceCount: Int,
    val avgWordsPerSentence: Double,
    val emotionalTone: String,
    val formalityLevel: String,
    val timestamp: Long
)

data class SenderProfile(
    val senderId: String,
    val communicationStyle: String,
    val avgResponseTime: Long,
    val preferredLength: String,
    val emotionalPatterns: List<String>,
    val messageCount: Int
)