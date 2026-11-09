package com.alingo.agent.client

import android.util.Log
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class WifiClient(private val server: String, private val token: String) {

    companion object {
        private const val TAG = "WifiClient"
    }

    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    private var isConnected = false
    private var lastCheck = 0L
    private val checkInterval = 30000L  // 30 sec

    fun isConnected(): Boolean {
        val now = System.currentTimeMillis()
        if (now - lastCheck < checkInterval) return isConnected

        // Quick check via heartbeat
        try {
            val request = Request.Builder()
                .url("$server/health")
                .get()
                .build()

            client.newCall(request).execute().use { response ->
                isConnected = response.isSuccessful
                lastCheck = now
            }
        } catch (e: Exception) {
            isConnected = false
            lastCheck = now
        }
        return isConnected
    }

    fun register(deviceUid: String, token: String): Boolean {
        return try {
            val json = JSONObject().apply {
                put("device_uid", deviceUid)
                put("enrollment_token", token)
                put("platform", "android")
            }

            val request = Request.Builder()
                .url("$server/api/v1/agent/register")
                .post(json.toString().toRequestBody("application/json".toMediaType()))
                .build()

            client.newCall(request).execute().use { response ->
                response.isSuccessful
            }
        } catch (e: Exception) {
            Log.e(TAG, "Register: ${e.message}")
            false
        }
    }

    fun pollCommands(): List<Map<String, Any?>>? {
        return try {
            val request = Request.Builder()
                .url("$server/api/v1/agent/commands/pending")
                .addHeader("Authorization", "Bearer $token")
                .get()
                .build()

            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) return null
                val text = response.body?.string() ?: return emptyList()
                val arr = org.json.JSONArray(text)
                val list = mutableListOf<Map<String, Any?>>()
                for (i in 0 until arr.length()) {
                    val obj = arr.getJSONObject(i)
                    val map = mutableMapOf<String, Any?>()
                    obj.keys().forEach { key -> map[key] = obj.get(key) }
                    list.add(map)
                }
                list
            }
        } catch (e: Exception) {
            Log.e(TAG, "Poll: ${e.message}")
            null
        }
    }

    fun sendCommand(command: Map<String, Any?>): Map<String, Any?>? {
        return try {
            val json = JSONObject(command).toString()
            val request = Request.Builder()
                .url("$server/api/v1/agent/results")
                .addHeader("Authorization", "Bearer $token")
                .post(json.toRequestBody("application/json".toMediaType()))
                .build()

            client.newCall(request).execute().use { response ->
                if (response.isSuccessful) mapOf("success" to true) else null
            }
        } catch (e: Exception) {
            Log.e(TAG, "Send: ${e.message}")
            null
        }
    }
}
