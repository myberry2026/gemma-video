package com.gemma.videomemory.llm

import android.util.Base64
import android.util.Log
import com.google.ai.edge.litertlm.Backend
import com.google.ai.edge.litertlm.Capabilities
import com.google.ai.edge.litertlm.Content
import com.google.ai.edge.litertlm.Contents
import com.google.ai.edge.litertlm.Conversation
import com.google.ai.edge.litertlm.ConversationConfig
import com.google.ai.edge.litertlm.Engine
import com.google.ai.edge.litertlm.EngineConfig
import com.google.ai.edge.litertlm.ExperimentalApi
import com.google.ai.edge.litertlm.ExperimentalFlags
import com.google.ai.edge.litertlm.Message
import com.google.ai.edge.litertlm.MessageCallback
import com.google.ai.edge.litertlm.OpenApiTool
import com.google.ai.edge.litertlm.SamplerConfig
import com.google.ai.edge.litertlm.ToolProvider
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.withContext

data class InferenceResult(
    val text: String?,
    val thinking: String?,
    val error: String?,
    val toolCalls: List<ToolCallResult>? = null,
    val benchmark: BenchmarkMetrics? = null,
)

data class ToolCallResult(
    val name: String,
    val arguments: Map<String, Any?>,
)

data class BenchmarkMetrics(
    val ttftMs: Long,
    val totalTimeMs: Long,
    val outputChars: Int,
    val tokensPerSec: Double,
)

object LlmInferenceManager {
    private const val TAG = "LlmInference"

    private var engine: Engine? = null
    private var conversation: Conversation? = null
    var isLoaded = false
        private set
    var modelPath: String? = null
        private set
    var supportsSpeculativeDecoding = false
        private set
    var currentBackend: String = "gpu"
        private set

    fun makeBackend(name: String, nativeLibraryDir: String? = null): Backend {
        return when (name.lowercase()) {
            "gpu" -> Backend.GPU()
            "npu" -> Backend.NPU(nativeLibraryDir ?: "/data/data/com.gemma.videomemory/lib")
            else -> Backend.CPU()
        }
    }

    @OptIn(ExperimentalApi::class)
    suspend fun loadModel(path: String, backend: String = "gpu") = withContext(Dispatchers.IO) {
        if (isLoaded && modelPath == path) {
            Log.d(TAG, "Model already loaded: $path")
            return@withContext
        }
        unload()

        Log.i(TAG, "Loading model: $path (backend=$backend)")
        val startTime = System.currentTimeMillis()

        try {
            // Check speculative decoding support
            try {
                val caps = Capabilities(path)
                supportsSpeculativeDecoding = caps.hasSpeculativeDecodingSupport()
                caps.close()
                Log.i(TAG, "Speculative decoding supported: $supportsSpeculativeDecoding")
            } catch (e: Exception) {
                Log.w(TAG, "Capabilities check failed: ${e.message}")
                supportsSpeculativeDecoding = false
            }

            // Force disable for GPU testing
            supportsSpeculativeDecoding = false
            if (supportsSpeculativeDecoding) {
                ExperimentalFlags.enableSpeculativeDecoding = true
            }

            val selectedBackend = makeBackend(backend)
            val engineConfig = EngineConfig(
                modelPath = path,
                backend = selectedBackend,
                visionBackend = if (selectedBackend is Backend.GPU) Backend.GPU() else Backend.CPU(),
                audioBackend = Backend.CPU(),
                maxNumTokens = 4096,
            )

            val newEngine = Engine(engineConfig)
            newEngine.initialize()

            // Reset experimental flags
            ExperimentalFlags.enableSpeculativeDecoding = null

            engine = newEngine
            modelPath = path
            currentBackend = backend.lowercase()
            isLoaded = true

            Log.i(TAG, "Model loaded in ${System.currentTimeMillis() - startTime}ms (speculative=$supportsSpeculativeDecoding)")
        } catch (e: Exception) {
            ExperimentalFlags.enableSpeculativeDecoding = null
            Log.e(TAG, "Model load failed: ${e.message}", e)
            throw e
        }
    }

    suspend fun infer(
        systemPrompt: String?,
        initialMessages: List<Pair<String, String>>,
        prompt: Contents,
        temperature: Double = 1.0,
        topP: Double = 0.95,
        topK: Int = 64,
        seed: Int = 0,
        tools: List<ToolProvider>? = null,
    ): InferenceResult = withContext(Dispatchers.IO) {
        val eng = engine ?: return@withContext InferenceResult(null, null, "Model not loaded")

        try { conversation?.close() } catch (e: Exception) { Log.w(TAG, "Conversation close failed: ${e.message}") }
        val historyMessages = buildHistory(initialMessages)
        // NPU/TPU don't support SamplerConfig
        val samplerConfig = if (currentBackend == "npu" || currentBackend == "tpu") null
            else SamplerConfig(topK, topP, temperature, seed)
        val convConfig = ConversationConfig(
            samplerConfig = samplerConfig,
            systemInstruction = systemPrompt?.let { Contents.of(it) },
            initialMessages = historyMessages,
            tools = tools ?: listOf(),
            automaticToolCalling = false,
        )

        val newConversation = eng.createConversation(convConfig)
        conversation = newConversation

        val result = CompletableDeferred<InferenceResult>()
        val responseBuilder = StringBuilder()
        var thinkingBuilder: StringBuilder? = null
        val collectedToolCalls = mutableListOf<ToolCallResult>()
        var firstTokenTime = 0L
        val startTime = System.currentTimeMillis()

        newConversation.sendMessageAsync(
            prompt,
            object : MessageCallback {
                override fun onMessage(message: Message) {
                    if (firstTokenTime == 0L) firstTokenTime = System.currentTimeMillis()
                    responseBuilder.append(message.toString())
                    // Collect thinking
                    val thinking = message.channels?.get("thought")
                    if (thinking != null) {
                        if (thinkingBuilder == null) thinkingBuilder = StringBuilder()
                        thinkingBuilder!!.append(thinking)
                    }
                    // Collect tool calls
                    for (tc in message.toolCalls) {
                        collectedToolCalls.add(ToolCallResult(tc.name, tc.arguments))
                    }
                }

                override fun onDone() {
                    val endTime = System.currentTimeMillis()
                    val chars = responseBuilder.length
                    val elapsed = endTime - startTime
                    result.complete(InferenceResult(
                        text = responseBuilder.toString(),
                        thinking = thinkingBuilder?.toString(),
                        error = null,
                        toolCalls = collectedToolCalls.ifEmpty { null },
                        benchmark = BenchmarkMetrics(
                            ttftMs = if (firstTokenTime > 0) firstTokenTime - startTime else 0,
                            totalTimeMs = elapsed,
                            outputChars = chars,
                            tokensPerSec = if (elapsed > 0) chars.toDouble() / elapsed * 1000 / 4 else 0.0,
                        ),
                    ))
                }

                override fun onError(throwable: Throwable) {
                    result.complete(InferenceResult(
                        text = responseBuilder.toString().ifEmpty { null },
                        thinking = thinkingBuilder?.toString(),
                        error = throwable.message ?: "Unknown error",
                        toolCalls = collectedToolCalls.ifEmpty { null },
                        benchmark = BenchmarkMetrics(
                            ttftMs = if (firstTokenTime > 0) firstTokenTime - startTime else 0,
                            totalTimeMs = System.currentTimeMillis() - startTime,
                            outputChars = responseBuilder.length,
                            tokensPerSec = 0.0,
                        ),
                    ))
                }
            },
            mapOf("enable_thinking" to "true"),
        )

        result.await()
    }

    fun inferStreaming(
        systemPrompt: String?,
        initialMessages: List<Pair<String, String>>,
        prompt: Contents,
        temperature: Double = 1.0,
        topP: Double = 0.95,
        topK: Int = 64,
        seed: Int = 0,
    ): Flow<InferenceResult> = callbackFlow {
        val eng = engine ?: run {
            trySend(InferenceResult(null, null, "Model not loaded"))
            close()
            return@callbackFlow
        }

        try { conversation?.close() } catch (e: Exception) { Log.w(TAG, "Conversation close failed: ${e.message}") }
        val historyMessages = buildHistory(initialMessages)
        // NPU/TPU don't support SamplerConfig
        val samplerConfig = if (currentBackend == "npu" || currentBackend == "tpu") null
            else SamplerConfig(topK, topP, temperature, seed)
        val convConfig = ConversationConfig(
            samplerConfig = samplerConfig,
            systemInstruction = systemPrompt?.let { Contents.of(it) },
            initialMessages = historyMessages,
        )

        val newConversation = eng.createConversation(convConfig)
        conversation = newConversation

        newConversation.sendMessageAsync(
            prompt,
            object : MessageCallback {
                override fun onMessage(message: Message) {
                    val text = message.toString()
                    val thinking = message.channels?.get("thought")
                    trySend(InferenceResult(text, thinking, null))
                }

                override fun onDone() { close() }
                override fun onError(throwable: Throwable) {
                    trySend(InferenceResult(null, null, throwable.message))
                    close()
                }
            },
            mapOf("enable_thinking" to "true"),
        )

        awaitClose { }
    }

    fun stopInference() {
        try { conversation?.cancelProcess() } catch (e: Exception) {
            Log.w(TAG, "Cancel failed: ${e.message}")
        }
    }

    fun unload() {
        try { conversation?.close() } catch (e: Exception) {
            Log.w(TAG, "Error closing conversation: ${e.message}")
        }
        conversation = null
        try { engine?.close() } catch (e: Exception) {
            Log.w(TAG, "Error closing engine: ${e.message}")
        }
        engine = null
        isLoaded = false
        modelPath = null
        currentBackend = "gpu"
        supportsSpeculativeDecoding = false
    }

    fun listModels(): List<Map<String, Any>> {
        val searchPaths = listOf(
            "/data/local/tmp",
            "/sdcard/Download",
            "/storage/emulated/0/Download",
            "/storage/emulated/0/Android/data/com.gemma.videomemory/files/models",
        )
        val models = mutableListOf<Map<String, Any>>()
        for (dir in searchPaths) {
            val f = java.io.File(dir)
            if (f.isDirectory) {
                f.listFiles()?.filter { it.name.endsWith(".litertlm") }?.forEach {
                    models.add(mapOf("name" to it.nameWithoutExtension, "path" to it.absolutePath, "size" to it.length()))
                }
            }
        }
        return models
    }

    fun decodeBase64Image(base64Str: String): ByteArray? {
        return try {
            Base64.decode(base64Str.substringAfter(","), Base64.DEFAULT)
        } catch (e: Exception) {
            Log.w(TAG, "Failed to decode base64: ${e.message}")
            null
        }
    }

    private fun buildHistory(initialMessages: List<Pair<String, String>>): List<Message> {
        return initialMessages.map { (role, content) ->
            when (role) {
                "user" -> Message.user(content)
                "assistant" -> Message.model(content)
                else -> Message.user(content)
            }
        }
    }
}
