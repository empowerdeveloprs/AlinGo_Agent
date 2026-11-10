package com.alingo.agent.handlers

import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume

object MicHandler {
    // Placeholder
    suspend fun record(durationSeconds: Int): Map<String, Any?> =
        suspendCancellableCoroutine { cont ->
            cont.resume(mapOf(
                "error" to "mic placeholder",
                "duration" to durationSeconds
            ))
        }
}
