package com.gemma.videomemory.llm

import android.util.Log
import com.google.ai.edge.litertlm.Content
import com.google.ai.edge.litertlm.Contents
import com.google.ai.edge.litertlm.OpenApiTool
import com.google.ai.edge.litertlm.ToolProvider
import com.google.ai.edge.litertlm.tool
import fi.iki.elonen.NanoHTTPD
import kotlinx.coroutines.flow.collect
import kotlinx.coroutines.runBlocking
import org.json.JSONArray
import org.json.JSONObject
import java.io.PipedInputStream
import java.io.PipedOutputStream
import java.util.UUID
import kotlin.concurrent.thread

class EmbeddedLlmServer(port: Int = 8080) : NanoHTTPD(port) {
    companion object {
        private const val TAG = "EmbeddedLlmServer"
    }

    override fun serve(session: IHTTPSession): Response {
        val corsHeaders = mapOf(
            "Access-Control-Allow-Origin" to "*",
            "Access-Control-Allow-Methods" to "POST, GET, OPTIONS",
            "Access-Control-Allow-Headers" to "Content-Type, Authorization",
        )

        if (session.method == Method.OPTIONS) {
            return newFixedLengthResponse(Response.Status.OK, "text/plain", "").apply {
                corsHeaders.forEach { (k, v) -> addHeader(k, v) }
            }
        }

        return when {
            session.uri == "/health" -> handleHealth(corsHeaders)
            session.uri == "/cancel" && session.method == Method.POST -> handleCancel(corsHeaders)
            session.uri == "/models" && session.method == Method.GET -> handleListModels(corsHeaders)
            session.uri == "/models/load" && session.method == Method.POST -> handleLoadModel(session, corsHeaders)
            session.uri == "/models/unload" && session.method == Method.POST -> handleUnloadModel(corsHeaders)
            session.uri == "/v1/chat/completions" && session.method == Method.POST ->
                handleChatCompletions(session, corsHeaders)
            else -> newFixedLengthResponse(Response.Status.NOT_FOUND, "text/plain", "Not Found")
        }
    }

    private fun handleHealth(corsHeaders: Map<String, String>): Response {
        val status = JSONObject().apply {
            put("status", "ok")
            put("model_loaded", LlmInferenceManager.isLoaded)
            put("model_path", LlmInferenceManager.modelPath ?: "")
            put("supports_speculative_decoding", LlmInferenceManager.supportsSpeculativeDecoding)
        }
        return jsonResponse(Response.Status.OK, status, corsHeaders)
    }

    private fun handleCancel(corsHeaders: Map<String, String>): Response {
        LlmInferenceManager.stopInference()
        return jsonResponse(Response.Status.OK, JSONObject().apply { put("success", true) }, corsHeaders)
    }

    private fun handleListModels(corsHeaders: Map<String, String>): Response {
        val models = LlmInferenceManager.listModels()
        val arr = JSONArray()
        for (m in models) {
            arr.put(JSONObject().apply { m.forEach { (k, v) -> put(k, v) } })
        }
        return jsonResponse(Response.Status.OK, JSONObject().apply { put("models", arr) }, corsHeaders)
    }

    private fun handleLoadModel(session: IHTTPSession, corsHeaders: Map<String, String>): Response {
        try {
            val bodyMap = HashMap<String, String>()
            session.parseBody(bodyMap)
            val req = JSONObject(bodyMap["postData"] ?: "{}")
            val path = req.optString("path", "")
            val backend = req.optString("backend", "gpu")
            if (path.isBlank()) return errorResponse("Missing 'path' field", corsHeaders)
            runBlocking { LlmInferenceManager.loadModel(path, backend) }
            return jsonResponse(Response.Status.OK, JSONObject().apply {
                put("success", true); put("model_path", path); put("backend", backend)
            }, corsHeaders)
        } catch (e: Exception) {
            return errorResponse("Load failed: ${e.message}", corsHeaders)
        }
    }

    private fun handleUnloadModel(corsHeaders: Map<String, String>): Response {
        LlmInferenceManager.unload()
        return jsonResponse(Response.Status.OK, JSONObject().apply { put("success", true) }, corsHeaders)
    }

    private fun handleChatCompletions(session: IHTTPSession, corsHeaders: Map<String, String>): Response {
        try {
            val bodyMap = HashMap<String, String>()
            session.parseBody(bodyMap)
            val request = JSONObject(bodyMap["postData"] ?: "")
            val messages = request.getJSONArray("messages")

            // Dynamic model loading
            val requestedModel = request.optString("model", "")
            if (requestedModel.isNotBlank() && !LlmInferenceManager.isLoaded) {
                findModelByName(requestedModel)?.let {
                    Log.i(TAG, "Dynamic load: $it")
                    runBlocking { LlmInferenceManager.loadModel(it) }
                }
            }
            if (!LlmInferenceManager.isLoaded) {
                findDefaultModel()?.let {
                    Log.i(TAG, "Auto-loading: $it")
                    runBlocking { LlmInferenceManager.loadModel(it) }
                } ?: return errorResponse("Model not loaded and no .litertlm file found", corsHeaders)
            }

            // Parse params
            val temperature = request.optDouble("temperature", 1.0)
            val topP = request.optDouble("top_p", 0.95)
            val topK = request.optInt("top_k", 64)
            val seed = request.optInt("seed", 0)
            val stream = request.optBoolean("stream", false)

            // Parse tools
            val tools = parseTools(request)

            // Parse messages
            var systemPrompt: String? = null
            val historyMessages = mutableListOf<Pair<String, String>>()
            var lastUserContents: Contents? = null

            for (i in 0 until messages.length()) {
                val msg = messages.getJSONObject(i)
                val role = msg.getString("role")
                val content = msg.get("content")

                when (role) {
                    "system" -> {
                        systemPrompt = if (content is JSONArray) extractTextFromContentArray(content) else content.toString()
                    }
                    "user", "assistant" -> {
                        if (i < messages.length() - 1) {
                            val text = if (content is JSONArray) extractTextFromContentArray(content) else content.toString()
                            historyMessages.add(role to text)
                        } else {
                            lastUserContents = parseContent(content)
                        }
                    }
                    "tool" -> {
                        // Tool response — add as user message with tool result
                        val text = if (content is String) content else content.toString()
                        historyMessages.add("user" to "[Tool Result]\n$text")
                    }
                }
            }

            if (lastUserContents == null) return errorResponse("No user message found", corsHeaders)

            return if (stream) {
                handleStreamingResponse(systemPrompt, historyMessages, lastUserContents, temperature, topP, topK, seed, corsHeaders)
            } else {
                handleBlockingResponse(systemPrompt, historyMessages, lastUserContents, temperature, topP, topK, seed, tools, corsHeaders)
            }

        } catch (e: Exception) {
            Log.e(TAG, "Request error: ${e.message}", e)
            return errorResponse("Internal error: ${e.message}", corsHeaders)
        }
    }

    private fun handleBlockingResponse(
        systemPrompt: String?, history: List<Pair<String, String>>, prompt: Contents,
        temperature: Double, topP: Double, topK: Int, seed: Int,
        tools: List<ToolProvider>?,
        corsHeaders: Map<String, String>,
    ): Response {
        val result = runBlocking {
            LlmInferenceManager.infer(systemPrompt, history, prompt, temperature, topP, topK, seed, tools)
        }

        if (result.error != null && result.text == null) {
            return errorResponse("Inference failed: ${result.error}", corsHeaders)
        }

        val bm = result.benchmark
        val modelName = LlmInferenceManager.modelPath?.substringAfterLast("/")?.removeSuffix(".litertlm") ?: "unknown"

        val response = JSONObject().apply {
            put("id", "chatcmpl-${UUID.randomUUID()}")
            put("object", "chat.completion")
            put("created", System.currentTimeMillis() / 1000)
            put("model", modelName)
            put("choices", JSONArray().apply {
                put(JSONObject().apply {
                    put("index", 0)
                    put("message", JSONObject().apply {
                        put("role", "assistant")
                        put("content", result.text ?: "")
                        if (result.thinking != null) put("reasoning_content", result.thinking)
                        // Tool calls
                        if (result.toolCalls != null && result.toolCalls.isNotEmpty()) {
                            put("tool_calls", JSONArray().apply {
                                for ((idx, tc) in result.toolCalls.withIndex()) {
                                    put(JSONObject().apply {
                                        put("id", "call_${UUID.randomUUID()}")
                                        put("type", "function")
                                        put("function", JSONObject().apply {
                                            put("name", tc.name)
                                            put("arguments", JSONObject(tc.arguments).toString())
                                        })
                                    })
                                }
                            })
                            put("content", JSONObject.NULL)
                        }
                    })
                    put("finish_reason", if (result.toolCalls.isNullOrEmpty()) "stop" else "tool_calls")
                })
            })
            put("usage", JSONObject().apply {
                val promptTokens = (history.joinToString(" ") { it.second }.length / 4).coerceAtLeast(1)
                val completionTokens = ((result.text?.length ?: 0) / 4).coerceAtLeast(1)
                put("prompt_tokens", promptTokens)
                put("completion_tokens", completionTokens)
                put("total_tokens", promptTokens + completionTokens)
            })
            if (bm != null) {
                put("benchmark", JSONObject().apply {
                    put("ttft_ms", bm.ttftMs)
                    put("total_ms", bm.totalTimeMs)
                    put("output_chars", bm.outputChars)
                    put("tokens_per_sec", bm.tokensPerSec)
                })
            }
        }

        return jsonResponse(Response.Status.OK, response, corsHeaders)
    }

    private fun handleStreamingResponse(
        systemPrompt: String?, history: List<Pair<String, String>>, prompt: Contents,
        temperature: Double, topP: Double, topK: Int, seed: Int,
        corsHeaders: Map<String, String>,
    ): Response {
        val pipedOut = PipedOutputStream()
        val pipedIn = PipedInputStream(pipedOut)
        val requestId = "chatcmpl-${UUID.randomUUID()}"
        val createdTime = System.currentTimeMillis() / 1000
        val modelName = LlmInferenceManager.modelPath?.substringAfterLast("/")?.removeSuffix(".litertlm") ?: "unknown"

        thread {
            try {
                runBlocking {
                    LlmInferenceManager.inferStreaming(systemPrompt, history, prompt, temperature, topP, topK, seed).collect { res ->
                        val chunk = JSONObject().apply {
                            put("id", requestId)
                            put("object", "chat.completion.chunk")
                            put("created", createdTime)
                            put("model", modelName)
                            put("choices", JSONArray().apply {
                                put(JSONObject().apply {
                                    put("index", 0)
                                    put("delta", JSONObject().apply {
                                        res.text?.let { put("content", it) }
                                        res.thinking?.let { put("reasoning_content", it) }
                                    })
                                    put("finish_reason", JSONObject.NULL)
                                })
                            })
                        }
                        pipedOut.write("data: ${chunk}\n\n".toByteArray())
                        pipedOut.flush()
                    }
                }
                val finalChunk = JSONObject().apply {
                    put("id", requestId)
                    put("object", "chat.completion.chunk")
                    put("created", createdTime)
                    put("model", modelName)
                    put("choices", JSONArray().apply {
                        put(JSONObject().apply {
                            put("index", 0)
                            put("delta", JSONObject())
                            put("finish_reason", "stop")
                        })
                    })
                }
                pipedOut.write("data: ${finalChunk}\n\n".toByteArray())
                pipedOut.write("data: [DONE]\n\n".toByteArray())
                pipedOut.flush()
            } catch (e: Exception) {
                Log.e(TAG, "Streaming error: ${e.message}")
            } finally {
                pipedOut.close()
            }
        }

        return newChunkedResponse(Response.Status.OK, "text/event-stream", pipedIn).apply {
            corsHeaders.forEach { (k, v) -> addHeader(k, v) }
            addHeader("Cache-Control", "no-cache")
            addHeader("Connection", "keep-alive")
        }
    }

    /**
     * Parse OpenAI-format tools array into LiteRT-LM ToolProvider list.
     * Uses OpenApiTool interface + tool() conversion function.
     */
    private fun parseTools(request: JSONObject): List<ToolProvider>? {
        if (!request.has("tools")) return null
        val toolsArray = request.getJSONArray("tools")
        if (toolsArray.length() == 0) return null

        val providers = mutableListOf<ToolProvider>()
        for (i in 0 until toolsArray.length()) {
            val tool = toolsArray.getJSONObject(i)
            if (tool.optString("type") != "function") continue
            val func = tool.getJSONObject("function")
            val funcName = func.getString("name")
            val funcDesc = func.optString("description", "")
            val params = func.optJSONObject("parameters")

            // Build OpenAPI-format tool description JSON
            val descJson = org.json.JSONObject().apply {
                put("name", funcName)
                put("description", funcDesc)
                if (params != null) put("parameters", params)
            }
            val descString = descJson.toString()

            val openApiTool = object : OpenApiTool {
                override fun getToolDescriptionJsonString(): String = descString
                override fun execute(arguments: String): String {
                    // Return arguments as-is — caller handles execution
                    return """{"tool_call":"$funcName","arguments":$arguments}"""
                }
            }

            providers.add(tool(openApiTool))
        }
        return providers.ifEmpty { null }
    }

    private fun parseContent(content: Any): Contents {
        if (content is String) return Contents.of(content)
        if (content !is JSONArray) return Contents.of(content.toString())

        val parts = mutableListOf<Content>()
        for (j in 0 until content.length()) {
            val item = content.getJSONObject(j)
            when (item.optString("type")) {
                "text" -> parts.add(Content.Text(item.getString("text")))
                "image_url" -> {
                    LlmInferenceManager.decodeBase64Image(item.getJSONObject("image_url").getString("url"))
                        ?.let { parts.add(Content.ImageBytes(it)) }
                }
                "audio_url" -> {
                    LlmInferenceManager.decodeBase64Image(item.getJSONObject("audio_url").getString("url"))
                        ?.let { parts.add(Content.AudioBytes(it)) }
                }
                "input_audio" -> {
                    LlmInferenceManager.decodeBase64Image(item.getJSONObject("input_audio").getString("data"))
                        ?.let { parts.add(Content.AudioBytes(it)) }
                }
            }
        }
        return if (parts.size == 1 && parts[0] is Content.Text) Contents.of((parts[0] as Content.Text).text) else Contents.of(parts)
    }

    private fun extractTextFromContentArray(content: JSONArray): String {
        return (0 until content.length())
            .map { content.getJSONObject(it) }
            .filter { it.getString("type") == "text" }
            .joinToString("\n") { it.getString("text") }
    }

    private fun findModelByName(name: String): String? {
        return LlmInferenceManager.listModels().firstOrNull {
            it["name"].toString().contains(name, ignoreCase = true) ||
            it["path"].toString().contains(name, ignoreCase = true)
        }?.get("path")?.toString()
    }

    private fun findDefaultModel(): String? {
        return LlmInferenceManager.listModels().firstOrNull()?.get("path")?.toString()
    }

    private fun jsonResponse(status: Response.Status, body: JSONObject, headers: Map<String, String>): Response {
        return newFixedLengthResponse(status, "application/json", body.toString()).apply {
            headers.forEach { (k, v) -> addHeader(k, v) }
        }
    }

    private fun errorResponse(message: String, headers: Map<String, String>): Response {
        val body = JSONObject().apply {
            put("error", JSONObject().apply {
                put("message", message)
                put("type", "server_error")
            })
        }
        return jsonResponse(Response.Status.INTERNAL_ERROR, body, headers)
    }
}
