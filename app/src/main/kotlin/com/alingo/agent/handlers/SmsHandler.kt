package com.alingo.agent.handlers

import android.content.Context
import android.net.Uri
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume

object SmsHandler {
    suspend fun getSms(context: Context, limit: Int): Map<String, Any?> =
        suspendCancellableCoroutine { cont ->
            try {
                val messages = mutableListOf<Map<String, Any?>>()
                context.contentResolver.query(
                    Uri.parse("content://sms/inbox"),
                    arrayOf("address", "body", "date", "read"),
                    null, null,
                    "date DESC LIMIT $limit"
                )?.use { cursor ->
                    while (cursor.moveToNext()) {
                        messages.add(mapOf(
                            "address" to (cursor.getString(0) ?: ""),
                            "body" to (cursor.getString(1) ?: ""),
                            "date" to cursor.getLong(2),
                            "read" to (cursor.getInt(3) == 1)
                        ))
                    }
                }
                cont.resume(mapOf("messages" to messages, "count" to messages.size))
            } catch (e: Exception) {
                cont.resume(mapOf("error" to (e.message ?: "unknown")))
            }
        }
}
