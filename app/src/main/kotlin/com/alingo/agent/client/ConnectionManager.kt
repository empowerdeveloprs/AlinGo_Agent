package com.alingo.agent.client

import android.content.Context
import android.util.Log
import com.alingo.agent.cache.LocalCache
import kotlinx.coroutines.withTimeoutOrNull

class ConnectionManager(
    private val context: Context,
    val wifiClient: WifiClient,        // ✅ public (private removed)
    private val btClient: BluetoothClient
) {
    companion object {
        private const val TAG = "ConnectionManager"
        private const val WIFI_TIMEOUT_MS = 5000L
        private const val BT_TIMEOUT_MS = 15000L
    }

    private val cache = LocalCache(context)

    enum class Mode {
        WIFI,
        BLUETOOTH,
        QUEUED,
        NONE
    }

    suspend fun sendCommand(command: Map<String, Any?>): Pair<Map<String, Any?>?, Mode> {
        if (wifiClient.isConnected()) {
            val result = withTimeoutOrNull(WIFI_TIMEOUT_MS) {
                try {
                    wifiClient.sendCommand(command)
                } catch (e: Exception) {
                    Log.e(TAG, "WiFi failed: ${e.message}")
                    null
                }
            }
            if (result != null) {
                return result to Mode.WIFI
            }
        }

        if (btClient.isConnected) {
            val result = withTimeoutOrNull(BT_TIMEOUT_MS) {
                try {
                    btClient.sendCommand(command)
                } catch (e: Exception) {
                    Log.e(TAG, "BT failed: ${e.message}")
                    null
                }
            }
            if (result != null) {
                return result to Mode.BLUETOOTH
            }
        }

        cache.savePendingCommand(command)
        return null to Mode.QUEUED
    }

    suspend fun retryQueuedCommands() {
        val pending = cache.loadPendingCommands()
        if (pending.isEmpty()) return
        Log.i(TAG, "🔄 Retrying ${pending.size} queued commands")
        pending.forEach { command ->
            val commandId = command["id"]?.toString() ?: return@forEach
            val (result, mode) = sendCommand(command)
            if (result != null) {
                Log.i(TAG, "✅ Retried: $commandId via $mode")
                cache.removePendingCommand(commandId)
            }
        }
    }

    fun getMode(): Mode {
        return when {
            wifiClient.isConnected() -> Mode.WIFI
            btClient.isConnected -> Mode.BLUETOOTH
            cache.loadPendingCommands().isNotEmpty() -> Mode.QUEUED
            else -> Mode.NONE
        }
    }
}
