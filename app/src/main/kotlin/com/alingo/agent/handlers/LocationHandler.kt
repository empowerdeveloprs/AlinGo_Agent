package com.alingo.agent.handlers

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import androidx.core.content.ContextCompat
import com.google.android.gms.location.*
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume

object LocationHandler {
    @SuppressLint("MissingPermission")
    suspend fun getLocation(context: Context): Map<String, Any?> =
        suspendCancellableCoroutine { cont ->
            if (ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION)
                != PackageManager.PERMISSION_GRANTED) {
                cont.resume(mapOf("error" to "Location permission not granted"))
                return@suspendCancellableCoroutine
            }

            try {
                val client = LocationServices.getFusedLocationProviderClient(context)
                client.getCurrentLocation(Priority.PRIORITY_HIGH_ACCURACY, null)
                    .addOnSuccessListener { loc ->
                        if (loc != null) {
                            cont.resume(mapOf(
                                "latitude" to loc.latitude,
                                "longitude" to loc.longitude,
                                "accuracy" to loc.accuracy,
                                "altitude" to loc.altitude,
                                "speed" to loc.speed,
                                "provider" to loc.provider
                            ))
                        } else {
                            cont.resume(mapOf("error" to "Location unavailable"))
                        }
                    }
                    .addOnFailureListener { e ->
                        cont.resume(mapOf("error" to (e.message ?: "unknown")))
                    }
            } catch (e: Exception) {
                cont.resume(mapOf("error" to (e.message ?: "exception")))
            }
        }
}
