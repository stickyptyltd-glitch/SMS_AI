package au.st1cky.smsautoframe.notify

import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import au.st1cky.smsautoframe.overlay.OverlayBus

class SmartNotificationListener: NotificationListenerService() {
    override fun onNotificationPosted(sbn: StatusBarNotification) {
        val pkg = sbn.packageName ?: return
        val text = (sbn.notification.extras.getCharSequence("android.text") ?: "").toString()
        val title = (sbn.notification.extras.getCharSequence("android.title") ?: "").toString()
        if (text.isBlank()) return
            if (pkg.contains("sms") || pkg.contains("messag") || pkg.contains("whatsapp")) {
                OverlayBus.onIncoming(this, if (title.isBlank()) pkg else title, text, isSms = false)
            }
    }
}
