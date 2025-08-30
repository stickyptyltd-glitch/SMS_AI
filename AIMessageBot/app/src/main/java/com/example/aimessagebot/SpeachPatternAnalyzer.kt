// SpeechPatternAnalyzer.kt
package com.example.aimessagebot

import java.util.concurrent.ConcurrentHashMap

class SpeechPatternAnalyzer {
    private val senderProfiles = ConcurrentHashMap<String, MutableList<MessageAnalysis>>()

    fun analyzeSender(senderId: String, message: String): SenderProfile {
        val analysis = analyzeMessage(message)

        // Store analysis for this sender
        senderProfiles.computeIfAbsent(senderId) { mutableListOf() }.add(analysis)

        // Build profile from historical data
        return buildSenderProfile(senderId)
    }

    private fun analyzeMessage(message: String): MessageAnalysis {
        val words = message.split("\\s+".toRegex())
        val sentences = message.split("[.!?]+".toRegex()).filter { it.isNotBlank() }

        return MessageAnalysis(
            wordCount = words.size,
            sentenceCount = sentences.size,
            avgWordsPerSentence = if (sentences.isNotEmpty()) words.size.toDouble() / sentences.size else 0.0,
            emotionalTone = detectEmotionalTone(message),
            formalityLevel = detectFormalityLevel(message),
            timestamp = System.currentTimeMillis()
        )
    }

    private fun buildSenderProfile(senderId: String): SenderProfile {
        val analyses = senderProfiles[senderId] ?: return getDefaultProfile(senderId)

        val avgWordCount = analyses.map { it.wordCount }.average()
        val communicationStyle = determineCommunicationStyle(analyses)
        val emotionalPatterns = analyses.map { it.emotionalTone }.distinct()

        return SenderProfile(
            senderId = senderId,
            communicationStyle = communicationStyle,
            avgResponseTime = calculateAvgResponseTime(analyses),
            preferredLength = when {
                avgWordCount < 10 -> "short"
                avgWordCount < 30 -> "medium"
                else -> "long"
            },
            emotionalPatterns = emotionalPatterns,
            messageCount = analyses.size
        )
    }

    private fun detectEmotionalTone(message: String): String {
        val lowerMessage = message.lowercase()

        return when {
            lowerMessage.contains(Regex("haha|lol|😂|😄|😊")) -> "happy"
            lowerMessage.contains(Regex("sad|😢|😞|☹️")) -> "sad"
            lowerMessage.contains(Regex("angry|mad|😠|😡")) -> "angry"
            lowerMessage.contains(Regex("excited|awesome|amazing|!{2,}")) -> "excited"
            else -> "neutral"
        }
    }

    private fun detectFormalityLevel(message: String): String {
        val formalIndicators = listOf("please", "thank you", "regards", "sincerely")
        val informalIndicators = listOf("hey", "haha", "lol", "gonna", "wanna")

        val formalScore = formalIndicators.count { message.lowercase().contains(it) }
        val informalScore = informalIndicators.count { message.lowercase().contains(it) }

        return when {
            formalScore > informalScore -> "formal"
            informalScore > formalScore -> "informal"
            else -> "neutral"
        }
    }

    private fun determineCommunicationStyle(analyses: List<MessageAnalysis>): String {
        val formalityLevels = analyses.map { it.formalityLevel }
        val avgWordCount = analyses.map { it.wordCount }.average()

        return when {
            formalityLevels.count { it == "formal" } > analyses.size / 2 -> "professional"
            avgWordCount < 15 -> "concise"
            analyses.any { it.emotionalTone != "neutral" } -> "expressive"
            else -> "casual"
        }
    }

    private fun calculateAvgResponseTime(analyses: List<MessageAnalysis>): Long {
        if (analyses.size < 2) return 0L

        val intervals = analyses.zipWithNext { a, b -> b.timestamp - a.timestamp }
        return intervals.average().toLong()
    }

    private fun getDefaultProfile(senderId: String) = SenderProfile(
        senderId = senderId,
        communicationStyle = "casual",
        avgResponseTime = 0L,
        preferredLength = "medium",
        emotionalPatterns = listOf("neutral"),
        messageCount = 0
    )
}