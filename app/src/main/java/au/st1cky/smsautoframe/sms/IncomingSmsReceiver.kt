package au.st1cky.smsautoframe.sms

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.Telephony
import au.st1cky.smsautoframe.overlay.OverlayBus

class IncomingSmsReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (Telephony.Sms.Intents.SMS_RECEIVED_ACTION == intent.action) {
            val msgs = Telephony.Sms.Intents.getMessagesFromIntent(intent)
            val from = msgs.firstOrNull()?.originatingAddress ?: "Unknown"
            val body = msgs.joinToString("") { it.messageBody }
            OverlayBus.onIncoming(context, from ?: "Unknown", body, isSms = true)
        }
    }
}
