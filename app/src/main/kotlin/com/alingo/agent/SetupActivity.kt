package com.alingo.agent

import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity

class SetupActivity : AppCompatActivity() {
    private val TAG = "SetupActivity"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val prefs = getSharedPreferences("alingo_agent", MODE_PRIVATE)

        intent?.data?.let { data ->
            Log.i(TAG, "Deep link: $data")
            handleDeepLink(data, prefs)
            return
        }

        if (prefs.getBoolean("registered", false)) {
            startService()
            finish()
            return
        }

        Toast.makeText(this, "Use the setup link from AlinGo admin", Toast.LENGTH_LONG).show()
        finish()
    }

    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        intent?.data?.let { data ->
            handleDeepLink(data, getSharedPreferences("alingo_agent", MODE_PRIVATE))
        }
    }

    private fun handleDeepLink(uri: Uri, prefs: android.content.SharedPreferences) {
        if (uri.scheme != "alingo-agent" || uri.host != "register") {
            finish()
            return
        }

        val alingoUrl = uri.getQueryParameter("url") ?: ""
        val uid = uri.getQueryParameter("uid") ?: ""
        val token = uri.getQueryParameter("token") ?: ""

        if (alingoUrl.isEmpty() || uid.isEmpty() || token.isEmpty()) {
            Toast.makeText(this, "Invalid setup link", Toast.LENGTH_LONG).show()
            finish()
            return
        }

        prefs.edit().apply {
            putString("alingo_url", alingoUrl)
            putString("device_uid", uid)
            putString("agent_token", token)
            putBoolean("registered", true)
            apply()
        }

        Log.i(TAG, "Registered: $uid @ $alingoUrl")
        Toast.makeText(this, "AlinGo Agent configured", Toast.LENGTH_SHORT).show()
        startService()
        finish()
    }

    private fun startService() {
        val i = Intent(this, AgentService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(i)
        } else {
            startService(i)
        }
    }
}
