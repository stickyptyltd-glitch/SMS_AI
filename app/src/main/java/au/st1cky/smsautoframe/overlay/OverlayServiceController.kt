package au.st1cky.smsautoframe.overlay

import android.content.Context
import android.content.Intent

object OverlayServiceController {
    fun show(ctx: Context, contact: String, incoming: String, draft: String, conf: Double, willAuto: Boolean, isSms: Boolean, goal: String? = null, sentiment: String? = null, summary: String? = null) {
        val i = Intent(ctx, OverlayService::class.java).apply {
            action = "SHOW"
            putExtra("contact", contact)
            putExtra("incoming", incoming)
            putExtra("draft", draft)
            putExtra("confidence", conf)
            putExtra("auto", willAuto)
            putExtra("isSms", isSms)
            putExtra("goal", goal ?: "")
            putExtra("sentiment", sentiment ?: "")
            putExtra("summary", summary ?: "")
        }
        ctx.startService(i)
    }
}
