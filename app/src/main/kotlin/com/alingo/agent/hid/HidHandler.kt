package com.alingo.agent.hid

import android.bluetooth.*
import android.content.Context
import android.os.Build
import android.util.Log
import java.util.concurrent.Executor

class HidHandler(private val context: Context) {

    companion object {
        private const val TAG = "HidHandler"
        private val KEYBOARD_REPORT_DESCRIPTOR = byteArrayOf(
            0x05, 0x01, 0x09, 0x06, 0xA1.toByte(), 0x01,
            0x05, 0x07, 0x19, 0xE0.toByte(), 0x29, 0xE7.toByte(),
            0x15, 0x00, 0x25, 0x01, 0x75, 0x01, 0x95.toByte(), 0x08,
            0x81.toByte(), 0x02, 0x95.toByte(), 0x01, 0x75, 0x08,
            0x81.toByte(), 0x01, 0x95.toByte(), 0x05, 0x75, 0x01,
            0x05, 0x08, 0x19, 0x01, 0x29, 0x05, 0x91.toByte(), 0x02,
            0x95.toByte(), 0x01, 0x75, 0x03, 0x91.toByte(), 0x01,
            0x95.toByte(), 0x06, 0x75, 0x08, 0x15, 0x00, 0x25, 0x65,
            0x05, 0x07, 0x19, 0x00, 0x29, 0x65, 0x81.toByte(), 0x00,
            0xC0.toByte()
        )
    }

    private var hidDevice: BluetoothHidDevice? = null
    private var isRegistered = false

    fun start(onReady: (Boolean) -> Unit) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.P) {
            onReady(false)
            return
        }

        val manager = context.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
        val adapter = manager.adapter

        adapter.getProfileProxy(context, object : BluetoothProfile.ServiceListener {
            override fun onServiceConnected(profile: Int, proxy: BluetoothProfile) {
                if (profile == BluetoothProfile.HID_DEVICE) {
                    hidDevice = proxy as BluetoothHidDevice
                    registerApp(onReady)
                }
            }

            override fun onServiceDisconnected(profile: Int) {
                hidDevice = null
                isRegistered = false
            }
        }, BluetoothProfile.HID_DEVICE)
    }

    private fun registerApp(onReady: (Boolean) -> Unit) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.P) {
            onReady(false)
            return
        }

        val sdp = BluetoothHidDeviceAppSdpSettings(
            "AlinGo Keyboard",
            "System Keyboard",
            "AlinGo",
            BluetoothHidDevice.SUBCLASS1_KEYBOARD,
            KEYBOARD_REPORT_DESCRIPTOR
        )

        val executor = Executor { it.run() }

        hidDevice?.registerApp(sdp, null, null, executor) {
            isRegistered = true
            Log.i(TAG, "HID registered")
            onReady(true)
        }
    }

    fun typeText(text: String) {
        if (!isRegistered) return
        text.forEach { char ->
            val keyCode = charToHidKeyCode(char)
            if (keyCode != 0) sendKey(keyCode)
        }
    }

    fun pressKey(keyCode: Int) {
        if (!isRegistered) return
        sendKey(keyCode)
    }

    private fun sendKey(keyCode: Int) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.P) return
        val press = byteArrayOf(0, 0, keyCode.toByte(), 0, 0, 0, 0, 0)
        val release = ByteArray(8)
        hidDevice?.sendReport(0, press)
        Thread.sleep(30)
        hidDevice?.sendReport(0, release)
        Thread.sleep(30)
    }

    private fun charToHidKeyCode(char: Char): Int {
        return when (char.lowercaseChar()) {
            'a' -> 0x04; 'b' -> 0x05; 'c' -> 0x06; 'd' -> 0x07
            'e' -> 0x08; 'f' -> 0x09; 'g' -> 0x0A; 'h' -> 0x0B
            'i' -> 0x0C; 'j' -> 0x0D; 'k' -> 0x0E; 'l' -> 0x0F
            'm' -> 0x10; 'n' -> 0x11; 'o' -> 0x12; 'p' -> 0x13
            'q' -> 0x14; 'r' -> 0x15; 's' -> 0x16; 't' -> 0x17
            'u' -> 0x18; 'v' -> 0x19; 'w' -> 0x1A; 'x' -> 0x1B
            'y' -> 0x1C; 'z' -> 0x1D
            '0' -> 0x27; '1' -> 0x1E; '2' -> 0x1F; '3' -> 0x20
            '4' -> 0x21; '5' -> 0x22; '6' -> 0x23; '7' -> 0x24
            '8' -> 0x25; '9' -> 0x26
            ' ' -> 0x2C; '\n' -> 0x28
            else -> 0x00
        }
    }

    fun stop() {
        try { hidDevice?.unregisterApp() } catch (e: Exception) {}
        isRegistered = false
    }
}
