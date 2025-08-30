package au.st1cky.smsautoframe.overlay

import android.app.*
import android.content.Intent
import android.graphics.PixelFormat
import android.os.Build
import android.os.IBinder
import android.view.*
import android.widget.*
import androidx.core.app.NotificationCompat
import au.st1cky.smsautoframe.R
import au.st1cky.smsautoframe.sms.SmsSenderService
import au.st1cky.smsautoframe.util.Prefs
import au.st1cky.smsautoframe.net.ReplyClient
import au.st1cky.smsautoframe.net.FeedbackRequest
import kotlinx.coroutines.*

class OverlayService: Service() {
    private var wm: WindowManager? = null
        private var overlay: View? = null

            override fun onCreate() {
                super.onCreate()
                startForegroundNoti()
                wm = getSystemService(WINDOW_SERVICE) as WindowManager
            }

            private fun startForegroundNoti() {
                val ch = "overlay_ch"
                if (Build.VERSION.SDK_INT >= 26) {
                    val mgr = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
                    mgr.createNotificationChannel(NotificationChannel(ch, "Overlay", NotificationManager.IMPORTANCE_LOW))
                }
                val n = NotificationCompat.Builder(this, ch)
                .setContentTitle("Auto-Reply running")
                .setSmallIcon(android.R.drawable.ic_dialog_info).build()
                startForeground(1, n)
            }

            override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
                if (intent?.action == "SHOW") {
                    val contact = intent.getStringExtra("contact") ?: "Unknown"
                    val incoming = intent.getStringExtra("incoming") ?: ""
                    val draft = intent.getStringExtra("draft") ?: ""
                    val conf = intent.getDoubleExtra("confidence", 0.0)
                    val willAuto = intent.getBooleanExtra("auto", false)
                    val isSms = intent.getBooleanExtra("isSms", true)
                    val goal = intent.getStringExtra("goal") ?: ""
                    val sentiment = intent.getStringExtra("sentiment") ?: ""
                    val summary = intent.getStringExtra("summary") ?: ""
                    showOverlay(contact, incoming, draft, conf, willAuto, isSms, goal, sentiment, summary)
                }
                return START_STICKY
            }

            private fun showOverlay(contact: String, incoming: String, draft: String, conf: Double, willAuto: Boolean, isSms: Boolean, goal: String, sentiment: String, summary: String) {
                removeOverlay()
                val inflater = LayoutInflater.from(this)
                overlay = inflater.inflate(R.layout.overlay_reply, null)

                overlay?.findViewById<TextView>(R.id.overlayContact)?.text = "$contact  •  conf=${"%.2f".format(conf)}  •  goal=${goal}  •  ${sentiment}"
                overlay?.findViewById<TextView>(R.id.overlayIncoming)?.text = incoming
                overlay?.findViewById<TextView>(R.id.overlaySummary)?.text = summary
                val edit = overlay?.findViewById<EditText>(R.id.overlayReply)
                edit?.setText(draft)

                // Never auto-send toggle for this contact
                overlay?.findViewById<CheckBox>(R.id.chkNeverThis)?.apply {
                    isChecked = Prefs(this@OverlayService).neverAutoMatches(contact)
                    setOnCheckedChangeListener { _, isChecked ->
                        val p = Prefs(this@OverlayService)
                        if (isChecked) p.addNeverAuto(contact) else p.removeNeverAuto(contact)
                        Toast.makeText(this@OverlayService, if (isChecked) "Added to Never Auto-Send" else "Removed from Never Auto-Send", Toast.LENGTH_SHORT).show()
                    }
                }

                fun collectTags(): Map<String, String> {
                    val helpful = overlay?.findViewById<CheckBox>(R.id.tagHelpful)?.isChecked == true
                    val tone = overlay?.findViewById<CheckBox>(R.id.tagTone)?.isChecked == true
                    val sharp = overlay?.findViewById<CheckBox>(R.id.tagSharp)?.isChecked == true
                    val goalMet = overlay?.findViewById<CheckBox>(R.id.tagGoalMet)?.isChecked == true
                    val proposed = overlay?.findViewById<CheckBox>(R.id.tagProposedTime)?.isChecked == true
                    val moved = overlay?.findViewById<CheckBox>(R.id.tagMovedToCall)?.isChecked == true
                    val asked = overlay?.findViewById<CheckBox>(R.id.tagAskedClarify)?.isChecked == true
                    val map = mutableMapOf<String,String>()
                    if (helpful) map["helpful"] = "true"
                    if (tone) map["needs_tone"] = "true"
                    if (sharp) map["too_sharp"] = "true"
                    if (goalMet) map["goal_met"] = "true"
                    if (proposed) map["proposed_time"] = "true"
                    if (moved) map["moved_to_call"] = "true"
                    if (asked) map["asked_clarify"] = "true"
                    return map
                }

                overlay?.findViewById<Button>(R.id.btnReject)?.setOnClickListener {
                    if (Prefs(this).learnMode()) sendFeedback(incoming, contact, draft, "", accepted=false, edited=false, tags=collectTags())
                        removeOverlay()
                }
                overlay?.findViewById<Button>(R.id.btnBetter)?.setOnClickListener {
                    Toast.makeText(this, "Marked for learning. Edit then Send.", Toast.LENGTH_SHORT).show()
                }
                overlay?.findViewById<Button>(R.id.btnSend)?.setOnClickListener {
                    val finalMsg = edit?.text?.toString() ?: ""
                    if (isSms) SmsSenderService.sendSms(contact, finalMsg)
                        val edited = finalMsg.trim() != draft.trim()
                        if (Prefs(this).learnMode()) sendFeedback(incoming, contact, draft, finalMsg, accepted=true, edited=edited, tags=collectTags())
                            removeOverlay()
                }

                val params = WindowManager.LayoutParams(
                    WindowManager.LayoutParams.MATCH_PARENT,
                    WindowManager.LayoutParams.WRAP_CONTENT,
                    if (Build.VERSION.SDK_INT >= 26) WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY else WindowManager.LayoutParams.TYPE_PHONE,
                        WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN or WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
                        PixelFormat.TRANSLUCENT
                )
                params.gravity = Gravity.TOP
                wm?.addView(overlay, params)

                if (willAuto) Toast.makeText(this, "Auto-send allowed for this contact.", Toast.LENGTH_SHORT).show()
            }

            private fun sendFeedback(incoming: String, contact: String, draft: String, finalMsg: String, accepted: Boolean, edited: Boolean, tags: Map<String,String>?) {
                CoroutineScope(Dispatchers.IO).launch {
                    try {
                        ReplyClient.instance(applicationContext).sendFeedback(
                            FeedbackRequest(
                                ts = java.time.Instant.now().toString(),
                                            incoming = incoming, contact = contact,
                                            draft = draft, final = finalMsg,
                                            accepted = accepted, edited = edited,
                                            tags = tags
                            )
                        )
                    } catch (_: Exception) {}
                }
            }

            private fun removeOverlay() {
                overlay?.let { wm?.removeView(it) }
                overlay = null
            }

            override fun onDestroy() { removeOverlay(); super.onDestroy() }
            override fun onBind(intent: Intent?): IBinder? = null
}
