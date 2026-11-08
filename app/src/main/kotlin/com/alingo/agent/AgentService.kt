package com.alingo.agent

import android.app.*
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.util.Log
import kotlinx.coroutines.*
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class AgentService : Service() {
    companion object {
        private const val TAG = "AgentService"
        private const val CH_ID = "alingo_agent"
        private const val NOTIF_ID = 1001
    }

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val http = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .build()

    private var alingoUrl = ""
    private var uid = ""
    private var token = ""
    private var running = false

    override fun onCreate() {
        super.onCreate()
        createChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (!running) {
            running = true
            val prefs = getSharedPreferences("alingo_agent", MODE_PRIVATE)
            alingoUrl = prefs.getString("alingo_url", "") ?: ""
            uid = prefs.getString("device_uid", "") ?: ""
            token = prefs.getString("agent_token", "") ?: ""

            startForeground(NOTIF_ID, buildNotification())
            startLoops()
        }
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        running = false
        scope.cancel()
        super.onDestroy()
    }

    private fun startLoops() {
        scope.launch {
            // Register
            launch { register() }
            // Heartbeat every 30s
            launch {
                while (running) {
                    try { heartbeat() } catch (_: Exception) {}
                    delay(30_000)
                }
            }
            // Poll every 10s
            launch {
                while (running) {
                    try { poll() } catch (_: Exception) {}
                    delay(10_000)
                }
            }
        }
    }

    private suspend fun register() {
        val body = JSONObject().apply {
            put("device_uid", uid)
            put("agent_token", token)
            put("platform", "android")
            put("model", Build.MODEL)
            put("os_version", Build.VERSION.RELEASE)
        }.toString()
        post("$alingoUrl/api/v1/agent/register", body, null)
        Log.i(TAG, "Registered as $uid")
    }

    private suspend fun heartbeat() {
        post("$alingoUrl/api/v1/agent/heartbeat", "{}", token)
    }

    private suspend fun poll() {
        val resp = get("$alingoUrl/api/v1/agent/commands/pending", token) ?: return
        if (resp.isEmpty() || resp == "[]") return
        val arr = JSONArray(resp)
        for (i in 0 until arr.length()) exec(arr.getJSONObject(i))
    }

    private suspend fun exec(cmd: JSONObject) {
        val id = cmd.getInt("id")
        val type = cmd.getString("command_type")

        post("$alingoUrl/api/v1/agent/commands/$id/ack", "{}", token)

        val result: Map<String, Any> = try {
            when (type) {
                "ping" -> mapOf("pong" to System.currentTimeMillis())
                "device_info" -> mapOf(
                    "model" to Build.MODEL,
                    "manufacturer" to Build.MANUFACTURER,
                    "android_version" to Build.VERSION.RELEASE,
                    "sdk_int" to Build.VERSION.SDK_INT,
                )
                else -> mapOf("note" to "Not implemented: $type")
            }
        } catch (e: Exception) {
            mapOf("error" to (e.message ?: "unknown"))
        }

        val body = JSONObject().apply {
            put("status", if (result.containsKey("error")) "failed" else "completed")
            put("result", JSONObject(result as Map<*, *>))
        }.toString()
        post("$alingoUrl/api/v1/agent/commands/$id/result", body, token)
    }

    private suspend fun post(url: String, body: String, tok: String?): String? =
        withContext(Dispatchers.IO) {
            try {
                val b = Request.Builder().url(url).post(body.toRequestBody("application/json".toMediaType()))
                if (tok != null) b.header("Authorization", "Bearer $tok")
                http.newCall(b.build()).execute().use { if (it.isSuccessful) it.body?.string() else null }
            } catch (_: Exception) { null }
        }

    private suspend fun get(url: String, tok: String?): String? =
        withContext(Dispatchers.IO) {
            try {
                val b = Request.Builder().url(url).get()
                if (tok != null) b.header("Authorization", "Bearer $tok")
                http.newCall(b.build()).execute().use { if (it.isSuccessful) it.body?.string() else null }
            } catch (_: Exception) { null }
        }

    private fun createChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val ch = NotificationChannel(CH_ID, "AlinGo Agent", NotificationManager.IMPORTANCE_MIN).apply {
                description = "Silent background agent"
                setShowBadge(false)
            }
            getSystemService(NotificationManager::class.java).createNotificationChannel(ch)
        }
    }

    private fun buildNotification(): Notification {
        val b = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
            Notification.Builder(this, CH_ID) else @Suppress("DEPRECATION") Notification.Builder(this)
        return b.setContentTitle("AlinGo Agent")
            .setContentText("Running")
            .setSmallIcon(android.R.drawable.stat_notify_sync)
            .setOngoing(true)
            .setPriority(Notification.PRIORITY_MIN)
            .build()
    }
}
