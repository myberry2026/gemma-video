package com.gemma.videomemory.llm

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.util.Log

class LlmService : Service() {
    companion object {
        private const val TAG = "LlmService"
        private const val CHANNEL_ID = "llm_service_channel"
        private const val NOTIFICATION_ID = 8080
        private const val SERVER_PORT = 8080

        var instance: LlmService? = null
            private set

        val isAlive: Boolean
            get() = instance != null

        fun start(context: Context) {
            val intent = Intent(context, LlmService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun stop(context: Context) {
            context.stopService(Intent(context, LlmService::class.java))
        }
    }

    private var server: EmbeddedLlmServer? = null

    override fun onCreate() {
        super.onCreate()
        instance = this
        createNotificationChannel()
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            startForeground(
                NOTIFICATION_ID, 
                createNotification(),
                ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE
            )
        } else {
            startForeground(NOTIFICATION_ID, createNotification())
        }

        try {
            server = EmbeddedLlmServer(SERVER_PORT)
            server?.start()
            Log.i(TAG, "LLM Server started on port $SERVER_PORT")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start LLM server: ${e.message}")
        }

        // Proactively pre-load model so agent requests don't block on first call
        Thread {
            try {
                val path = LlmInferenceManager.listModels().firstOrNull()?.get("path")?.toString()
                if (path != null) {
                    Log.i(TAG, "Pre-loading model: $path (backend=cpu)")
                    kotlinx.coroutines.runBlocking { LlmInferenceManager.loadModel(path, "cpu") }
                    Log.i(TAG, "Model pre-loaded successfully")
                } else {
                    Log.w(TAG, "No .litertlm model found for pre-load")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Model pre-load failed: ${e.message}")
            }
        }.start()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        return START_STICKY
    }

    override fun onDestroy() {
        server?.stop()
        server = null
        instance = null
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Gemma AI Inference",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Keeps the on-device LLM server running"
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    private fun createNotification(): Notification {
        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, CHANNEL_ID)
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(this)
        }

        return builder
            .setContentTitle("Gemma AI Online")
            .setContentText("On-device LLM server is active on port $SERVER_PORT")
            .setSmallIcon(android.R.drawable.ic_menu_info_details)
            .setOngoing(true)
            .build()
    }
}
