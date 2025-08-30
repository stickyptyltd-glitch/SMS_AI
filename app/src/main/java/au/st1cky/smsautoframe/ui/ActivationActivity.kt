package au.st1cky.smsautoframe.ui

import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import androidx.activity.ComponentActivity
import au.st1cky.smsautoframe.R
import au.st1cky.smsautoframe.net.ReplyClient
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class ActivationActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_activation)

        val tokenInput = findViewById<EditText>(R.id.licToken)
        val btnActivate = findViewById<Button>(R.id.btnActivate)
        val btnCheck = findViewById<Button>(R.id.btnCheckStatus)
        val btnHwid = findViewById<Button>(R.id.btnGetHwid)
        val out = findViewById<TextView>(R.id.licStatus)

        btnActivate.setOnClickListener {
            val token = tokenInput.text.toString().trim()
            if (token.isEmpty()) { toast("Paste activation token"); return@setOnClickListener }
            CoroutineScope(Dispatchers.IO).launch {
                try {
                    val res = ReplyClient.instance(this@ActivationActivity).activateLicense(token)
                    withContext(Dispatchers.Main) {
                        if (res.ok == true) out.text = "Activated successfully"
                        else out.text = "Activation failed: ${res.error ?: "unknown"}"
                    }
                } catch (e: Exception) {
                    withContext(Dispatchers.Main) { out.text = "Error: ${e.message}" }
                }
            }
        }

        btnCheck.setOnClickListener {
            CoroutineScope(Dispatchers.IO).launch {
                try {
                    val res = ReplyClient.instance(this@ActivationActivity).getLicenseStatus()
                    val status = res["status"]?.toString() ?: "unknown"
                    val tier = res["tier"]?.toString() ?: ""
                    val expires = res["expires"]?.toString() ?: ""
                    val days = res["days_remaining"]?.toString() ?: ""
                    withContext(Dispatchers.Main) {
                        out.text = "Status: $status\nTier: $tier\nExpires: $expires\nDays remaining: $days"
                    }
                } catch (e: Exception) {
                    withContext(Dispatchers.Main) { out.text = "Error: ${e.message}" }
                }
            }
        }

        btnHwid.setOnClickListener {
            CoroutineScope(Dispatchers.IO).launch {
                try {
                    val id = ReplyClient.instance(this@ActivationActivity).getHardwareId()
                    withContext(Dispatchers.Main) { out.text = "Hardware ID: $id" }
                } catch (e: Exception) {
                    withContext(Dispatchers.Main) { out.text = "Error: ${e.message}" }
                }
            }
        }
    }

    private fun toast(msg: String) {
        android.widget.Toast.makeText(this, msg, android.widget.Toast.LENGTH_SHORT).show()
    }
}

