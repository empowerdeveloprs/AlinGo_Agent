package com.alingo.agent.handlers

import android.content.Context
import android.provider.CallLog
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume

object CallLogHandler {
    suspend fun getCalls(context: Context, limit: Int): Map<String, Any?> =
        suspendCancellableCoroutine { cont ->
            try {
                val calls = mutableListOf<Map<String, Any?>>()
                context.contentResolver.query(
                    CallLog.Calls.CONTENT_URI,
                    arrayOf(
                        CallLog.Calls.NUMBER, CallLog.Calls.TYPE,
                        CallLog.Calls.DATE, CallLog.Calls.DURATION,
                        CallLog.Calls.CACHED_NAME
                    ),
                    null, null,
                    CallLog.Calls.DATE + " DESC LIMIT $limit"
                )?.use { cursor ->
                    while (cursor.moveToNext()) {
                        calls.add(mapOf(
                            "number" to (cursor.getString(0) ?: ""),
                            "type" to when (cursor.getInt(1)) {
                                CallLog.Calls.INCOMING_TYPE -> "incoming"
                                CallLog.Calls.OUTGOING_TYPE -> "outgoing"
                                CallLog.Calls.MISSED_TYPE -> "missed"
                                else -> "unknown"
                            },
                            "date" to cursor.getLong(2),
                            "duration" to cursor.getInt(3),
                            "contact_name" to (cursor.getString(4) ?: "")
                        ))
                    }
                }
                cont.resume(mapOf("calls" to calls, "count" to calls.size))
            } catch (e: Exception) {
                cont.resume(mapOf("error" to (e.message ?: "unknown")))
            }
        }
}
