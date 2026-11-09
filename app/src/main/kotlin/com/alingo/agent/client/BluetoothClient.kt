package com.alingo.agent.client

import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothSocket
import android.content.Context
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.util.UUID

class BluetoothClient(private val context: Context) {

    companion object {
        private const val TAG = "BtClient"
        private val SPP_UUID: UUID = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB")
    }

    private var socket: BluetoothSocket? = null
    private var writer: OutputStreamWriter? = null
    private var reader: BufferedReader? = null

    val isConnected: Boolean
        get() = socket?.isConnected == true

    suspend fun connect(deviceAddress: String): Boolean = withContext(Dispatchers.IO) {
        try {
            val adapter = BluetoothAdapter.getDefaultAdapter() ?: return@withContext false
            if (!adapter.isEnabled) return@withContext false

            val device: BluetoothDevice = adapter.getRemoteDevice(deviceAddress)
            socket = device.createRfcommSocketToServiceRecord(SPP_UUID)
            socket?.connect()

            writer = OutputStreamWriter(socket!!.outputStream)
            reader = BufferedReader(InputStreamReader(socket!!.inputStream))

            Log.i(TAG, "✅ Connected to $deviceAddress")
            true
        } catch (e: Exception) {
            Log.e(TAG, "Connect failed: ${e.message}")
            disconnect()
            false
        }
    }

    suspend fun sendCommand(command: Map<String, Any?>): Map<String, Any?>? = withContext(Dispatchers.IO) {
        if (!isConnected) return@withContext null

        try {
            val json = JSONObject(command).toString()
            writer?.write(json + "\n")
            writer?.flush()

            val response = reader?.readLine() ?: return@withContext null
            val jsonResponse = JSONObject(response)

            val result = mutableMapOf<String, Any?>()
            jsonResponse.keys().forEach { key ->
                result[key] = jsonResponse.get(key)
            }
            result
        } catch (e: Exception) {
            Log.e(TAG, "Send failed: ${e.message}")
            disconnect()
            null
        }
    }

    fun disconnect() {
        try {
            reader?.close()
            writer?.close()
            socket?.close()
        } catch (e: Exception) {
            Log.e(TAG, "Disconnect: ${e.message}")
        }
        socket = null
        reader = null
        writer = null
    }
}
