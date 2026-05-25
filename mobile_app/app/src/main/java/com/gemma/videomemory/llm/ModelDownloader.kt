package com.gemma.videomemory.llm

import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.URL
import kotlin.coroutines.coroutineContext

object ModelDownloader {
    private const val TAG = "ModelDownloader"
    private const val BUFFER_SIZE = 8192

    const val DEFAULT_MODEL_NAME = "Gemma-4-E2B-it"
    const val DEFAULT_MODEL_ID = "litert-community/gemma-4-E2B-it-litert-lm"
    const val DEFAULT_COMMIT_HASH = "6e5c4f1e395deb959c494953478fa5cec4b8008f"
    const val DEFAULT_MODEL_FILE = "gemma-4-E2B-it.litertlm"
    const val TOTAL_SIZE = 2588147712L // Precise size for Gemma-4-E2B-it.litertlm

    fun getDownloadUrl(modelId: String, commitHash: String, fileName: String): String {
        return "https://huggingface.co/$modelId/resolve/$commitHash/$fileName"
    }

    suspend fun download(
        urlStr: String,
        targetFile: File,
        accessToken: String? = null,
        onProgress: (received: Long, total: Long) -> Unit
    ): Boolean = withContext(Dispatchers.IO) {
        var connection: HttpURLConnection? = null
        try {
            val url = URL(urlStr)
            val tmpFile = File(targetFile.absolutePath + ".tmp")
            
            connection = url.openConnection() as HttpURLConnection
            if (accessToken != null) {
                connection.setRequestProperty("Authorization", "Bearer $accessToken")
            }

            val existingLength = if (tmpFile.exists()) tmpFile.length() else 0L
            if (existingLength > 0) {
                connection.setRequestProperty("Range", "bytes=$existingLength-")
            }

            connection.connect()
            val responseCode = connection.responseCode
            Log.i(TAG, "Response Code: $responseCode for $urlStr")

            if (responseCode != HttpURLConnection.HTTP_OK && responseCode != HttpURLConnection.HTTP_PARTIAL) {
                Log.e(TAG, "Server error: $responseCode")
                return@withContext false
            }

            val (startOffset, totalLength) = when (responseCode) {
                HttpURLConnection.HTTP_OK -> 0L to TOTAL_SIZE
                HttpURLConnection.HTTP_PARTIAL -> existingLength to TOTAL_SIZE
                else -> 0L to TOTAL_SIZE
            }

            val inputStream = connection.inputStream
            val outputStream = FileOutputStream(tmpFile, existingLength > 0 && responseCode == HttpURLConnection.HTTP_PARTIAL)
            
            val buffer = ByteArray(BUFFER_SIZE)
            var bytesRead: Int
            var currentReceived = startOffset
            var lastReportTime = 0L

            while (inputStream.read(buffer).also { bytesRead = it } != -1) {
                coroutineContext.ensureActive()
                outputStream.write(buffer, 0, bytesRead)
                currentReceived += bytesRead
                
                val now = System.currentTimeMillis()
                if (now - lastReportTime > 500) {
                    onProgress(currentReceived, totalLength)
                    lastReportTime = now
                }
            }
            
            outputStream.flush()
            outputStream.close()
            inputStream.close()
            
            if (tmpFile.renameTo(targetFile)) {
                onProgress(totalLength, totalLength)
                Log.i(TAG, "Download and rename SUCCESS: ${targetFile.absolutePath}")
                true
            } else {
                Log.e(TAG, "Failed to rename tmp file to target")
                false
            }
        } catch (e: Exception) {
            if (e is kotlinx.coroutines.CancellationException) {
                Log.i(TAG, "Download PAUSED (Cancelled by user)")
            } else {
                Log.e(TAG, "Download failed: ${e.message}", e)
                val tmpFile = File(targetFile.absolutePath + ".tmp")
                // We don't delete tmp file here to support resume
            }
            false
        } finally {
            connection?.disconnect()
        }
    }
}
