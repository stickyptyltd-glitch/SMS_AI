package au.st1cky.smsautoframe.sms

import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.telephony.SmsManager

class SmsSenderService: Service() {
    override fun onBind(intent: Intent?): IBinder? = null
    companion object {
        fun sendSms(phone: String, msg: String) {
            SmsManager.getDefault().sendTextMessage(phone, null, msg, null, null)
        }
    }
}
