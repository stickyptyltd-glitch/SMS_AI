package au.st1cky.smsautoframe.overlay

import android.content.Context
import au.st1cky.smsautoframe.net.ReplyClient
import au.st1cky.smsautoframe.util.Prefs
import au.st1cky.smsautoframe.sms.SmsSenderService
import kotlinx.coroutines.*

object OverlayBus {
    fun onIncoming(ctx: Context, contact: String, body: String, isSms: Boolean) {
        val prefs = Prefs(ctx)
        if (isSms && !prefs.enableSms()) return
            if (!isSms && !prefs.enableNotif()) return

                CoroutineScope(Dispatchers.IO).launch {
                    val client = ReplyClient.instance(ctx)
                    val res = client.getDraftWithMeta(body, contact)
                    val draft = (res.draft ?: res.reply ?: "").trim()
                    val sentiment = res.analysis?.sentiment ?: ""
                    val goal = res.goal ?: ""
                    val adjusted = estimateConfidence(body, draft, sentiment)
                    var summary = ""
                    try {
                        val sum = client.getMemorySummary(contact, 6)
                        summary = (sum.summary ?: "").trim()
                    } catch (_: Exception) {}
                    val allow = prefs.allowlist().split(",").map { it.trim() }.filter { it.isNotBlank() }
                    var willAutoSend = prefs.autoSend() &&
                    adjusted >= prefs.confThreshold() &&
                    allow.any { contact.contains(it, ignoreCase = true) || body.contains(it, ignoreCase = true) }
                    if (goal.startsWith("de-escalate")) {
                        willAutoSend = false
                    }
                    if (prefs.blockNegativeAutoSend() && sentiment.equals("negative", ignoreCase = true)) {
                        willAutoSend = false
                    }
                    if (prefs.neverAutoMatches(contact)) willAutoSend = false
                    if (!goal.startsWith("de-escalate") && prefs.alwaysAutoMatches(contact)) {
                        willAutoSend = true
                    }

                    OverlayServiceController.show(ctx, contact, body, draft, adjusted, willAutoSend, isSms, goal, sentiment, summary)
                    if (willAutoSend && isSms) {
                        SmsSenderService.sendSms(contact, draft)
                        // learning: accepted w/o edit
                        if (prefs.learnMode()) {
                            try {
                                client.sendFeedback(
                                    au.st1cky.smsautoframe.net.FeedbackRequest(
                                        ts = java.time.Instant.now().toString(),
                                                                               incoming = body, contact = contact,
                                                                               draft = draft, final = draft,
                                                                               accepted = true, edited = false
                                    )
                                )
                            } catch (_: Exception) {}
                        }
                    }
                }
    }

    private fun estimateConfidence(incoming: String, draft: String, sentiment: String): Double {
        val s = incoming.lowercase()
        var c = 0.85
        if (listOf("cheat", "seeing", "narcissist", "liar").any { it in s }) c = 0.65
        if (incoming.length < 12) c -= 0.05
        if (draft.length in 2..200) c += 0.05
        if (sentiment.equals("negative", ignoreCase = true)) c -= 0.05
        if (sentiment.equals("positive", ignoreCase = true)) c += 0.02
        return c.coerceIn(0.0, 1.0)
    }
}
