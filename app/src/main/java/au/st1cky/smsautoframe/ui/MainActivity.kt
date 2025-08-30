package au.st1cky.smsautoframe.ui

import android.Manifest
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import au.st1cky.smsautoframe.R
import au.st1cky.smsautoframe.overlay.OverlayService
import au.st1cky.smsautoframe.util.Prefs
import au.st1cky.smsautoframe.net.ReplyClient
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainActivity : ComponentActivity() {

    private val requestPerms = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val serverIp = findViewById<EditText>(R.id.serverIp)
        val autoSend = findViewById<CheckBox>(R.id.autoSendHighConfidence)
        val blockNeg = findViewById<CheckBox>(R.id.blockNegAutoSend)
        val btnStart = findViewById<Button>(R.id.btnStart)
        val status = findViewById<TextView>(R.id.status)
        val btnLicense = findViewById<Button>(R.id.btnLicense)
        val contactName = findViewById<EditText>(R.id.contactName)
        val btnShowSummary = findViewById<Button>(R.id.btnShowSummary)
        val btnPurgeMemory = findViewById<Button>(R.id.btnPurgeMemory)
        val memSummary = findViewById<TextView>(R.id.memSummary)
        val btnAddNever = findViewById<Button>(R.id.btnAddNeverAutoSend)
        val btnRemoveNever = findViewById<Button>(R.id.btnRemoveNeverAutoSend)
        val neverList = findViewById<TextView>(R.id.neverList)
        val btnAddAlways = findViewById<Button>(R.id.btnAddAlwaysAutoSend)
        val btnRemoveAlways = findViewById<Button>(R.id.btnRemoveAlwaysAutoSend)
        val alwaysList = findViewById<TextView>(R.id.alwaysList)
        val settingsFile = findViewById<EditText>(R.id.settingsFile)
        val btnExport = findViewById<Button>(R.id.btnExportSettings)
        val btnImport = findViewById<Button>(R.id.btnImportSettings)
        val testContact = findViewById<EditText>(R.id.testContact)
        val testIncoming = findViewById<EditText>(R.id.testIncoming)
        val btnTestReply = findViewById<Button>(R.id.btnTestReply)
        val testResult = findViewById<TextView>(R.id.testResult)

        serverIp.setText(Prefs(this).serverBase())
        autoSend.isChecked = Prefs(this).autoSend()
        blockNeg.isChecked = Prefs(this).blockNegativeAutoSend()

        btnStart.setOnClickListener {
            Prefs(this).setServerBase(serverIp.text.toString())
            Prefs(this).setAutoSend(autoSend.isChecked)
            Prefs(this).setBlockNegativeAutoSend(blockNeg.isChecked)
            ensurePermissions()
            startService(Intent(this, OverlayService::class.java))
            status.text = "Status: overlay started"
        }

        btnLicense.setOnClickListener {
            startActivity(Intent(this, ActivationActivity::class.java))
        }

        wireMemoryButtons(contactName, btnShowSummary, btnPurgeMemory, memSummary)
        wireTestReply(testContact, testIncoming, btnTestReply, testResult)
        wireNeverAutoSendButtons(contactName, btnAddNever, btnRemoveNever, neverList)
        neverList.text = "Never Auto-Send: ${Prefs(this).neverAutoDisplay()}"
    }

    private fun showToast(msg: String) {
        android.widget.Toast.makeText(this, msg, android.widget.Toast.LENGTH_SHORT).show()
    }

    private fun wireMemoryButtons(contactName: EditText, btnShow: Button, btnPurge: Button, out: TextView) {
        btnShow.setOnClickListener {
            val c = contactName.text.toString().trim()
            if (c.isEmpty()) { showToast("Enter contact name"); return@setOnClickListener }
            CoroutineScope(Dispatchers.IO).launch {
                try {
                    val res = ReplyClient.instance(this@MainActivity).getMemorySummary(c, 10)
                    withContext(Dispatchers.Main) { out.text = (res.summary ?: "(no summary)") }
                } catch (e: Exception) {
                    withContext(Dispatchers.Main) { out.text = "Error: ${e.message}" }
                }
            }
        }
        btnPurge.setOnClickListener {
            val c = contactName.text.toString().trim()
            if (c.isEmpty()) { showToast("Enter contact name"); return@setOnClickListener }
            CoroutineScope(Dispatchers.IO).launch {
                try {
                    val res = ReplyClient.instance(this@MainActivity).purgeMemory(c)
                    withContext(Dispatchers.Main) { out.text = if (res.ok == true) "Purged." else "Failed: ${res.error}" }
                } catch (e: Exception) {
                    withContext(Dispatchers.Main) { out.text = "Error: ${e.message}" }
                }
            }
        }
    }

    private fun wireTestReply(contact: EditText, incoming: EditText, btn: Button, out: TextView) {
        btn.setOnClickListener {
            val c = contact.text.toString().trim().ifEmpty { "Tester" }
            val inc = incoming.text.toString().trim()
            if (inc.isEmpty()) { showToast("Enter incoming text"); return@setOnClickListener }
            CoroutineScope(Dispatchers.IO).launch {
                try {
                    val res = au.st1cky.smsautoframe.net.ReplyClient.instance(this@MainActivity).getDraftWithMeta(inc, c)
                    val sb = StringBuilder()
                    sb.append("Draft: ").append(res.draft ?: res.reply ?: "").append('\n')
                    sb.append("Goal: ").append(res.goal ?: "").append("  Sentiment: ").append(res.analysis?.sentiment ?: "")
                    withContext(Dispatchers.Main) { out.text = sb.toString() }
                } catch (e: Exception) {
                    withContext(Dispatchers.Main) { out.text = "Error: ${e.message}" }
                }
            }
        }
    }

    private fun wireNeverAutoSendButtons(contactName: EditText, btnAdd: Button, btnRemove: Button, out: TextView) {
        btnAdd.setOnClickListener {
            val c = contactName.text.toString().trim()
            if (c.isEmpty()) { showToast("Enter contact name"); return@setOnClickListener }
            val prefs = Prefs(this)
            prefs.addNeverAuto(c)
            out.text = "Never Auto-Send: ${prefs.neverAutoDisplay()}"
            showToast("Added to Never Auto-Send: $c")
        }
        btnRemove.setOnClickListener {
            val c = contactName.text.toString().trim()
            if (c.isEmpty()) { showToast("Enter contact name"); return@setOnClickListener }
            val prefs = Prefs(this)
            prefs.removeNeverAuto(c)
            out.text = "Never Auto-Send: ${prefs.neverAutoDisplay()}"
            showToast("Removed from Never Auto-Send: $c")
        }
    }

    private fun ensurePermissions() {
        val perms = mutableListOf(
            Manifest.permission.RECEIVE_SMS,
            Manifest.permission.SEND_SMS,
            Manifest.permission.READ_SMS
        )
        if (Build.VERSION.SDK_INT >= 33) {
            perms.add(Manifest.permission.POST_NOTIFICATIONS)
        }
        requestPerms.launch(perms.toTypedArray())

        if (!Settings.canDrawOverlays(this)) {
            val intent = Intent(
                Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                Uri.parse("package:$packageName")
            )
            startActivity(intent)
        }
    }

    private fun wireAlwaysAutoSendButtons(contactName: EditText, btnAdd: Button, btnRemove: Button, out: TextView) {
        btnAdd.setOnClickListener {
            val c = contactName.text.toString().trim()
            if (c.isEmpty()) { showToast("Enter contact name"); return@setOnClickListener }
            val prefs = Prefs(this)
            prefs.addAlwaysAuto(c)
            out.text = "Always Auto-Send: ${Prefs(this).alwaysAutoDisplay()}"
            showToast("Added to Always Auto-Send: $c")
        }
        btnRemove.setOnClickListener {
            val c = contactName.text.toString().trim()
            if (c.isEmpty()) { showToast("Enter contact name"); return@setOnClickListener }
            val prefs = Prefs(this)
            prefs.removeAlwaysAuto(c)
            out.text = "Always Auto-Send: ${Prefs(this).alwaysAutoDisplay()}"
            showToast("Removed from Always Auto-Send: $c")
        }
    }

    private fun wireSettingsExportImport(fileName: EditText, btnExport: Button, btnImport: Button,
                                         serverIp: EditText, autoSend: CheckBox, blockNeg: CheckBox,
                                         neverList: TextView, alwaysList: TextView) {
        btnExport.setOnClickListener {
            val name = fileName.text.toString().trim().ifEmpty { "settings.json" }
            val prefs = Prefs(this)
            try {
                val obj = org.json.JSONObject()
                obj.put("server", prefs.serverBase())
                obj.put("autoSend", prefs.autoSend())
                obj.put("blockNeg", prefs.blockNegativeAutoSend())
                obj.put("allowlist", prefs.allowlist())
                obj.put("neverAuto", prefs.neverAutoSendList())
                obj.put("alwaysAuto", prefs.alwaysAutoSendList())
                obj.put("banned", prefs.bannedWords())
                obj.put("preferred", prefs.preferredPhrases())
                obj.put("thr", prefs.confThreshold())
                openFileOutput(name, MODE_PRIVATE).use { it.write(obj.toString(2).toByteArray()) }
                showToast("Exported to $filesDir/$name")
            } catch (e: Exception) {
                showToast("Export failed: ${e.message}")
            }
        }
        btnImport.setOnClickListener {
            val name = fileName.text.toString().trim().ifEmpty { "settings.json" }
            val prefs = Prefs(this)
            try {
                val text = openFileInput(name).bufferedReader().use { it.readText() }
                val obj = org.json.JSONObject(text)
                prefs.setServerBase(obj.optString("server", prefs.serverBase()))
                prefs.setAutoSend(obj.optBoolean("autoSend", prefs.autoSend()))
                prefs.setBlockNegativeAutoSend(obj.optBoolean("blockNeg", prefs.blockNegativeAutoSend()))
                prefs.setAllowlist(obj.optString("allowlist", prefs.allowlist()))
                prefs.setNeverAutoSendList(obj.optString("neverAuto", prefs.neverAutoSendList()))
                prefs.setAlwaysAutoSendList(obj.optString("alwaysAuto", prefs.alwaysAutoSendList()))
                prefs.setBannedWords(obj.optString("banned", prefs.bannedWords()))
                prefs.setPreferredPhrases(obj.optString("preferred", prefs.preferredPhrases()))
                prefs.setConfThreshold(obj.optDouble("thr", prefs.confThreshold()))
                // reflect in UI
                serverIp.setText(prefs.serverBase())
                autoSend.isChecked = prefs.autoSend()
                blockNeg.isChecked = prefs.blockNegativeAutoSend()
                neverList.text = "Never Auto-Send: ${Prefs(this).neverAutoDisplay()}"
                alwaysList.text = "Always Auto-Send: ${Prefs(this).alwaysAutoDisplay()}"
                showToast("Imported from $filesDir/$name")
            } catch (e: Exception) {
                showToast("Import failed: ${e.message}")
            }
        }
    }
}
