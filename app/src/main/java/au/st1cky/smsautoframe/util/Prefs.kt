package au.st1cky.smsautoframe.util

import android.content.Context
import android.content.SharedPreferences

class Prefs(ctx: Context) {
    private val sp: SharedPreferences = ctx.getSharedPreferences("prefs", Context.MODE_PRIVATE)

        fun serverBase(): String = sp.getString("server", "http://192.168.1.20:8081")!!
        fun setServerBase(v: String) = sp.edit().putString("server", v).apply()

        fun autoSend(): Boolean = sp.getBoolean("autoSend", false)
        fun setAutoSend(v: Boolean) = sp.edit().putBoolean("autoSend", v).apply()

        fun enableSms(): Boolean = sp.getBoolean("enableSms", true)
        fun setEnableSms(v: Boolean) = sp.edit().putBoolean("enableSms", v).apply()

        fun enableNotif(): Boolean = sp.getBoolean("enableNotif", true)
        fun setEnableNotif(v: Boolean) = sp.edit().putBoolean("enableNotif", v).apply()

        fun learnMode(): Boolean = sp.getBoolean("learnMode", true)
        fun setLearnMode(v: Boolean) = sp.edit().putBoolean("learnMode", v).apply()

        fun confThreshold(): Double = java.lang.Double.longBitsToDouble(sp.getLong("thr", java.lang.Double.doubleToLongBits(0.80)))
        fun setConfThreshold(v: Double) = sp.edit().putLong("thr", java.lang.Double.doubleToLongBits(v)).apply()

        fun allowlist(): String = sp.getString("allowlist", "Courtney")!!
        fun setAllowlist(v: String) = sp.edit().putString("allowlist", v).apply()

        fun bannedWords(): String = sp.getString("banned", "")!!
        fun setBannedWords(v: String) = sp.edit().putString("banned", v).apply()

        fun preferredPhrases(): String = sp.getString("preferred", "Sweet, let’s keep it chill.")!!
        fun setPreferredPhrases(v: String) = sp.edit().putString("preferred", v).apply()

        fun blockNegativeAutoSend(): Boolean = sp.getBoolean("blockNeg", true)
        fun setBlockNegativeAutoSend(v: Boolean) = sp.edit().putBoolean("blockNeg", v).apply()

        // Comma-separated list of contacts for which auto-send is never allowed (legacy)
        fun neverAutoSendList(): String = sp.getString("neverAuto", "")!!
        fun setNeverAutoSendList(v: String) = sp.edit().putString("neverAuto", v).apply()
        // JSON metadata for never list: array of objects { label, digits }
        private fun neverAutoJson(): String = sp.getString("neverAutoJson", "[]")!!
        private fun setNeverAutoJson(v: String) = sp.edit().putString("neverAutoJson", v).apply()

        private fun normalizePhone(s: String): String {
            val digits = s.filter { it.isDigit() }
            return digits
        }

        fun addNeverAuto(contact: String) {
            val token = run {
                val d = normalizePhone(contact)
                if (d.length >= 7) d else contact.trim()
            }
            val set = neverAutoSendList().split(",").map { it.trim() }.filter { it.isNotBlank() }.toMutableSet()
            set.add(token)
            setNeverAutoSendList(set.joinToString(", "))
            // update meta json
            try {
                val arr = org.json.JSONArray(neverAutoJson())
                var exists = false
                for (i in 0 until arr.length()) {
                    val o = arr.getJSONObject(i)
                    if (o.optString("label").equals(contact, true) || o.optString("digits") == normalizePhone(contact)) {
                        exists = true; break
                    }
                }
                if (!exists) {
                    val o = org.json.JSONObject()
                    o.put("label", contact.trim())
                    o.put("digits", normalizePhone(contact))
                    arr.put(o)
                    setNeverAutoJson(arr.toString())
                }
            } catch (_: Exception) {}
        }

        fun removeNeverAuto(contact: String) {
            val d = normalizePhone(contact)
            val set = neverAutoSendList().split(",").map { it.trim() }.filter { it.isNotBlank() }.toMutableSet()
            if (d.length >= 7) {
                set.removeIf { it.filter { ch -> ch.isDigit() } == d }
            }
            set.removeIf { it.equals(contact, ignoreCase = true) }
            setNeverAutoSendList(set.joinToString(", "))
            try {
                val arr = org.json.JSONArray(neverAutoJson())
                val keep = org.json.JSONArray()
                for (i in 0 until arr.length()) {
                    val o = arr.getJSONObject(i)
                    val od = o.optString("digits")
                    val ol = o.optString("label")
                    if (od.isNotEmpty() && d.isNotEmpty()) {
                        if (od == d) continue
                    }
                    if (ol.equals(contact, true)) continue
                    keep.put(o)
                }
                setNeverAutoJson(keep.toString())
            } catch (_: Exception) {}
        }

        fun neverAutoMatches(contact: String): Boolean {
            val d = normalizePhone(contact)
            val list = neverAutoSendList().split(",").map { it.trim() }.filter { it.isNotBlank() }
            for (t in list) {
                val td = t.filter { it.isDigit() }
                if (td.isNotEmpty() && d.isNotEmpty()) {
                    if (td == d) return true
                } else {
                    if (contact.contains(t, ignoreCase = true)) return true
                }
            }
            return false
        }

        fun neverAutoDisplay(): String {
            return try {
                val arr = org.json.JSONArray(neverAutoJson())
                val parts = mutableListOf<String>()
                for (i in 0 until arr.length()) {
                    val o = arr.getJSONObject(i)
                    val label = o.optString("label").ifEmpty { o.optString("digits") }
                    val digits = o.optString("digits")
                    parts.add(if (digits.isNotEmpty() && label != digits) "$label ($digits)" else label)
                }
                if (parts.isEmpty()) neverAutoSendList() else parts.joinToString(", ")
            } catch (e: Exception) {
                neverAutoSendList()
            }
        }

        // Always allow auto-send list (overrides blocks except de-escalation)
        fun alwaysAutoSendList(): String = sp.getString("alwaysAuto", "")!!
        fun setAlwaysAutoSendList(v: String) = sp.edit().putString("alwaysAuto", v).apply()
        fun addAlwaysAuto(contact: String) {
            val d = normalizePhone(contact)
            val token = if (d.length >= 7) d else contact.trim()
            val set = alwaysAutoSendList().split(",").map { it.trim() }.filter { it.isNotBlank() }.toMutableSet()
            set.add(token)
            setAlwaysAutoSendList(set.joinToString(", "))
        }
        fun removeAlwaysAuto(contact: String) {
            val d = normalizePhone(contact)
            val set = alwaysAutoSendList().split(",").map { it.trim() }.filter { it.isNotBlank() }.toMutableSet()
            if (d.length >= 7) set.removeIf { it.filter { ch -> ch.isDigit() } == d }
            set.removeIf { it.equals(contact, true) }
            setAlwaysAutoSendList(set.joinToString(", "))
        }
        fun alwaysAutoMatches(contact: String): Boolean {
            val d = normalizePhone(contact)
            val list = alwaysAutoSendList().split(",").map { it.trim() }.filter { it.isNotBlank() }
            for (t in list) {
                val td = t.filter { it.isDigit() }
                if (td.isNotEmpty() && d.isNotEmpty()) { if (td == d) return true }
                else if (contact.contains(t, true)) return true
            }
            return false
        }
        fun alwaysAutoDisplay(): String = alwaysAutoSendList()
}
