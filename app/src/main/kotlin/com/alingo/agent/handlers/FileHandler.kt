package com.alingo.agent.handlers

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.Settings
import android.util.Base64
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.util.Locale

object FileHandler {

    private const val TAG = "FileHandler"
    private const val MAX_DOWNLOAD_BYTES = 25L * 1024 * 1024
    private const val MAX_PREVIEW_BYTES  = 256L * 1024
    private val TEXT_EXTS = setOf(
        "txt","log","json","xml","csv","md","html","htm",
        "ini","conf","cfg","yml","yaml","kt","java","py",
        "js","ts","sh","bat","properties"
    )

    private fun hasStorageAccess(context: Context): Boolean =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R)
            Environment.isExternalStorageManager()
        else
            context.checkSelfPermission(android.Manifest.permission.READ_EXTERNAL_STORAGE) ==
                android.content.pm.PackageManager.PERMISSION_GRANTED

    private fun permissionError(): Map<String, Any?> = mapOf(
        "error" to "Storage permission not granted",
        "action_required" to "open_settings",
        "message" to "Grant 'All files access' for AlinGo Agent in Settings"
    )

    suspend fun listDirectory(context: Context, path: String?): Map<String, Any?> =
        withContext(Dispatchers.IO) {
            try {
                if (!hasStorageAccess(context)) return@withContext permissionError()
                val target = if (path.isNullOrBlank() || path == "/")
                    Environment.getExternalStorageDirectory().absolutePath else path
                val dir = File(target)
                if (!dir.exists())    return@withContext mapOf("error" to "Not found: $target")
                if (!dir.isDirectory) return@withContext mapOf("error" to "Not a directory: $target")
                if (!dir.canRead())   return@withContext mapOf("error" to "Cannot read: $target")

                val entries = dir.listFiles()?.map { f ->
                    mapOf(
                        "name"     to f.name,
                        "path"     to f.absolutePath,
                        "is_dir"   to f.isDirectory,
                        "size"     to f.length(),
                        "modified" to f.lastModified(),
                        "ext"      to f.extension.lowercase(Locale.ROOT)
                    )
                } ?: emptyList()

                val sorted = entries.sortedWith(
                    compareByDescending<Map<String, Any?>> { it["is_dir"] as Boolean }
                        .thenBy { (it["name"] as String).lowercase(Locale.ROOT) }
                )
                Log.i(TAG, "Listed ${sorted.size} in ${dir.absolutePath}")
                mapOf(
                    "path" to dir.absolutePath, "parent" to dir.parent,
                    "count" to sorted.size, "files" to sorted
                )
            } catch (e: Exception) {
                mapOf("error" to "List failed: ${e.message}")
            }
        }

    suspend fun readFile(context: Context, path: String?): Map<String, Any?> =
        withContext(Dispatchers.IO) {
            try {
                if (!hasStorageAccess(context)) return@withContext permissionError()
                if (path.isNullOrBlank()) return@withContext mapOf("error" to "Path required")
                val f = File(path)
                if (!f.exists() || !f.isFile) return@withContext mapOf("error" to "Not a file: $path")
                if (!f.canRead())             return@withContext mapOf("error" to "Cannot read: $path")

                val size = f.length()
                val isText = f.extension.lowercase(Locale.ROOT) in TEXT_EXTS
                when {
                    isText && size <= MAX_PREVIEW_BYTES -> mapOf(
                        "path" to f.absolutePath, "name" to f.name,
                        "size" to size, "type" to "text",
                        "content" to f.readText()
                    )
                    size <= MAX_PREVIEW_BYTES -> mapOf(
                        "path" to f.absolutePath, "name" to f.name,
                        "size" to size, "type" to "binary",
                        "content_base64" to Base64.encodeToString(f.readBytes(), Base64.NO_WRAP)
                    )
                    else -> mapOf(
                        "path" to f.absolutePath, "name" to f.name,
                        "size" to size, "type" to "too_large",
                        "message" to "Size ${size}B > ${MAX_PREVIEW_BYTES}B"
                    )
                }
            } catch (e: Exception) { mapOf("error" to "Read failed: ${e.message}") }
        }

    suspend fun download(context: Context, path: String?): Map<String, Any?> =
        withContext(Dispatchers.IO) {
            try {
                if (!hasStorageAccess(context)) return@withContext permissionError()
                if (path.isNullOrBlank()) return@withContext mapOf("error" to "Path required")
                val f = File(path)
                if (!f.exists() || !f.isFile) return@withContext mapOf("error" to "Not a file: $path")
                if (!f.canRead())             return@withContext mapOf("error" to "Cannot read: $path")
                if (f.length() > MAX_DOWNLOAD_BYTES)
                    return@withContext mapOf("error" to "Too large: ${f.length()}B")

                val bytes = f.readBytes()
                mapOf(
                    "path" to f.absolutePath, "name" to f.name,
                    "size" to bytes.size,
                    "content_base64" to Base64.encodeToString(bytes, Base64.NO_WRAP)
                )
            } catch (e: Exception) { mapOf("error" to "Download failed: ${e.message}") }
        }

    fun buildPermissionIntent(context: Context): Intent {
        val pkg = context.packageName
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R)
            Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION, Uri.parse("package:$pkg"))
        else
            Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:$pkg"))
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    }
}
