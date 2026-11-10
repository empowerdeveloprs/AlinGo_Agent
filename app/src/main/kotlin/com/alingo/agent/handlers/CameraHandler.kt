package com.alingo.agent.handlers

import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume

object CameraHandler {
    // Placeholder — returns 1x1 pixel for now
    suspend fun capture(facing: String): Map<String, Any?> =
        suspendCancellableCoroutine { cont ->
            val pixel = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
            cont.resume(mapOf(
                "image_base64" to pixel,
                "facing" to facing,
                "note" to "placeholder"
            ))
        }
}
