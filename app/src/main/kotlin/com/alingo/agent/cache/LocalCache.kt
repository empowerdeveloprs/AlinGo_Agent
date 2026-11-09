package com.alingo.agent.cache

import android.content.Context
import android.util.Log
import org.json.JSONObject
import java.io.File

class LocalCache(private val context: Context) {

    companion object {
        private const val TAG = "LocalCache"
        private const val PENDING_FILE = "pending_commands.json"
    }

    private val cacheFile = File(context.filesDir, PENDING_FILE)

    fun savePendingCommand(command: Map<String, Any?>) {
        try {
            val commandId = command["id"]?.toString() ?: return
            val pending = loadPendingCommands().toMutableList()
            pending.add(command)
            savePendingCommands(pending)
            Log.i(TAG, "💾 Saved: $commandId")
        } catch (e: Exception) {
            Log.e(TAG, "Save: ${e.message}")
        }
    }

    fun loadPendingCommands(): List<Map<String, Any?>> {
        if (!cacheFile.exists()) return emptyList()
        return try {
            val text = cacheFile.readText()
            val arr = org.json.JSONArray(text)
            val list = mutableListOf<Map<String, Any?>>()
            for (i in 0 until arr.length()) {
                val obj = arr.getJSONObject(i)
                val map = mutableMapOf<String, Any?>()
                obj.keys().forEach { key -> map[key] = obj.get(key) }
                list.add(map)
            }
            list
        } catch (e: Exception) {
            Log.e(TAG, "Load: ${e.message}")
            emptyList()
        }
    }

    fun removePendingCommand(commandId: String) {
        try {
            val pending = loadPendingCommands().toMutableList()
            pending.removeAll { it["id"]?.toString() == commandId }
            savePendingCommands(pending)
        } catch (e: Exception) {
            Log.e(TAG, "Remove: ${e.message}")
        }
    }

    fun saveResult(commandId: String, result: Map<String, Any?>) {
        val resultsFile = File(context.filesDir, "results_$commandId.json")
        try {
            resultsFile.writeText(JSONObject(result).toString())
            Log.i(TAG, "💾 Result saved: $commandId")
        } catch (e: Exception) {
            Log.e(TAG, "Save result: ${e.message}")
        }
    }

    fun getSavedResult(commandId: String): Map<String, Any?>? {
        val resultsFile = File(context.filesDir, "results_$commandId.json")
        if (!resultsFile.exists()) return null
        return try {
            val obj = JSONObject(resultsFile.readText())
            val map = mutableMapOf<String, Any?>()
            obj.keys().forEach { key -> map[key] = obj.get(key) }
            map
        } catch (e: Exception) {
            null
        }
    }

    fun clearResult(commandId: String) {
        File(context.filesDir, "results_$commandId.json").delete()
    }

    private fun savePendingCommands(commands: List<Map<String, Any?>>) {
        try {
            val arr = org.json.JSONArray()
            commands.forEach { arr.put(JSONObject(it)) }
            cacheFile.writeText(arr.toString())
        } catch (e: Exception) {
            Log.e(TAG, "Save pending: ${e.message}")
        }
    }
}
