package com.gemma.videomemory

import android.Manifest
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.util.Log
import android.provider.Settings
import android.text.TextUtils
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.GridLayoutManager
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import androidx.lifecycle.lifecycleScope
import coil.load
import com.gemma.videomemory.llm.LlmInferenceManager
import com.gemma.videomemory.llm.LlmService
import com.gemma.videomemory.llm.ModelDownloader
import kotlinx.coroutines.launch
import java.io.File
import java.text.SimpleDateFormat
import java.util.*

class MainActivity : AppCompatActivity() {
    companion object { private const val TAG = "MainActivity" }


    private val PERMISSION_REQUEST_CODE = 1001
    
    // UI Elements
    private lateinit var statusText: TextView
    private lateinit var statusDot: View
    private lateinit var statusLabel: TextView
    private lateinit var btnToggleAccessibility: Button
    private lateinit var btnStartLogging: Button
    private lateinit var btnStopLogging: Button
    private lateinit var editLlmUrl: android.widget.EditText
    private lateinit var rgLlmMode: android.widget.RadioGroup
    private lateinit var rbRemoteLlm: android.widget.RadioButton
    private lateinit var rbNativeLlm: android.widget.RadioButton
    private lateinit var btnManualRecap: Button
    
    // Model Management
    private lateinit var textModelStatus: TextView
    private lateinit var progressModelDownload: android.widget.ProgressBar
    private lateinit var btnDownloadModel: Button
    
    // Tabs container views
    private lateinit var tabSettingsLayout: View
    private lateinit var tabAlbumLayout: View
    private lateinit var tabStoryboardLayout: View
    
    // Tabs navigation buttons
    private lateinit var btnTabSettings: LinearLayout
    private lateinit var btnTabAlbum: LinearLayout
    private lateinit var btnTabStoryboard: LinearLayout
    
    private lateinit var textTabSettings: TextView
    private lateinit var textTabAlbum: TextView
    private lateinit var textTabStoryboard: TextView
    
    private lateinit var indicatorTabSettings: View
    private lateinit var indicatorTabAlbum: View
    private lateinit var indicatorTabStoryboard: View

    // Album components
    private lateinit var recyclerAlbum: RecyclerView
    private lateinit var textAlbumCount: TextView
    
    // Storyboard components
    private lateinit var recyclerStoryboard: RecyclerView
    private lateinit var layoutStoryboardBanner: View
    private lateinit var textStoryboardBannerLabel: TextView

    // Fullscreen Preview components
    private lateinit var layoutFullscreenPreview: FrameLayout
    private lateinit var imgFullscreenPreview: ImageView
    private lateinit var btnClosePreview: Button
    private lateinit var btnDeletePreview: Button
    private var selectedPreviewFile: File? = null

    // Base Directory
    private val baseDir = File(Environment.getExternalStorageDirectory(), "AetherLens")

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // Initialize UI Elements
        statusText = findViewById(R.id.text_status)
        statusDot = findViewById(R.id.view_status_dot)
        statusLabel = findViewById(R.id.text_status_label)
        btnToggleAccessibility = findViewById(R.id.btn_toggle_accessibility)
        btnStartLogging = findViewById(R.id.btn_start_logging)
        btnStopLogging = findViewById(R.id.btn_stop_logging)
        editLlmUrl = findViewById(R.id.edit_llm_url)
        rgLlmMode = findViewById(R.id.rg_llm_mode)
        rbRemoteLlm = findViewById(R.id.rb_remote_llm)
        rbNativeLlm = findViewById(R.id.rb_native_llm)
        btnManualRecap = findViewById(R.id.btn_manual_recap)

        // Model Management
        textModelStatus = findViewById(R.id.text_model_status)
        progressModelDownload = findViewById(R.id.progress_model_download)
        btnDownloadModel = findViewById(R.id.btn_download_model)

        btnDownloadModel.setOnClickListener {
            startModelDownload()
        }

        // Tabs container views
        tabSettingsLayout = findViewById(R.id.layout_tab_settings)
        tabAlbumLayout = findViewById(R.id.layout_tab_album)
        tabStoryboardLayout = findViewById(R.id.layout_tab_storyboard)

        // Tabs navigation buttons
        btnTabSettings = findViewById(R.id.btn_tab_settings)
        btnTabAlbum = findViewById(R.id.btn_tab_album)
        btnTabStoryboard = findViewById(R.id.btn_tab_storyboard)

        textTabSettings = findViewById(R.id.text_tab_settings)
        textTabAlbum = findViewById(R.id.text_tab_album)
        textTabStoryboard = findViewById(R.id.text_tab_storyboard)

        indicatorTabSettings = findViewById(R.id.indicator_tab_settings)
        indicatorTabAlbum = findViewById(R.id.indicator_tab_album)
        indicatorTabStoryboard = findViewById(R.id.indicator_tab_storyboard)

        // Album & Storyboard components
        recyclerAlbum = findViewById(R.id.recycler_album)
        textAlbumCount = findViewById(R.id.text_album_count)
        
        recyclerStoryboard = findViewById(R.id.recycler_storyboard)
        layoutStoryboardBanner = findViewById(R.id.layout_storyboard_banner)
        textStoryboardBannerLabel = findViewById(R.id.text_storyboard_banner_label)

        // Fullscreen Preview components
        layoutFullscreenPreview = findViewById(R.id.layout_fullscreen_preview)
        imgFullscreenPreview = findViewById(R.id.img_fullscreen_preview)
        btnClosePreview = findViewById(R.id.btn_close_preview)
        btnDeletePreview = findViewById(R.id.btn_delete_preview)

        // Set layout managers
        recyclerAlbum.layoutManager = GridLayoutManager(this, 3)
        recyclerStoryboard.layoutManager = LinearLayoutManager(this)

        // Set Tab Click Listeners
        btnTabStoryboard.setOnClickListener { switchTab(0) }
        btnTabAlbum.setOnClickListener { switchTab(1) }
        btnTabSettings.setOnClickListener { switchTab(2) }

        // Setup Accessibility Setting Button
        btnToggleAccessibility.setOnClickListener {
            val intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
            startActivity(intent)
            Toast.makeText(this, "Enable 'AetherLens Screen Memory Service' in Settings", Toast.LENGTH_LONG).show()
        }

        // Shared Preferences to store recording state
        val sharedPrefs = getSharedPreferences("AetherLensPrefs", Context.MODE_PRIVATE)

        // Initial UI State for LLM
        val currentLlmMode = sharedPrefs.getString("llm_mode", "remote")
        if (currentLlmMode == "native") {
            rbNativeLlm.isChecked = true
            editLlmUrl.setText(sharedPrefs.getString("llm_server_url_native", "http://localhost:8080/v1"))
        } else {
            rbRemoteLlm.isChecked = true
            editLlmUrl.setText(sharedPrefs.getString("llm_server_url_remote", "http://100.113.214.52:1234/v1"))
        }

        rgLlmMode.setOnCheckedChangeListener { _, checkedId ->
            if (checkedId == R.id.rb_remote_llm) {
                val url = sharedPrefs.getString("llm_server_url_remote", "http://100.113.214.52:1234/v1")
                sharedPrefs.edit()
                    .putString("llm_mode", "remote")
                    .putString("llm_server_url", url)
                    .apply()
                editLlmUrl.setText(url)
                LlmService.stop(this)
            } else {
                val url = sharedPrefs.getString("llm_server_url_native", "http://localhost:8080/v1")
                sharedPrefs.edit()
                    .putString("llm_mode", "native")
                    .putString("llm_server_url", url)
                    .apply()
                editLlmUrl.setText(url)
                LlmService.start(this)
            }
        }

        // Setup Control Buttons
        btnStartLogging.setOnClickListener {
            if (checkStoragePermissions()) {
                val url = editLlmUrl.text.toString().trim()
                val mode = if (rbRemoteLlm.isChecked) "remote" else "native"
                
                sharedPrefs.edit()
                    .putBoolean("is_recording", true)
                    .putString("llm_mode", mode)
                    .putString("llm_server_url_$mode", url)
                    .putString("llm_server_url", url) // current active
                    .apply()
                
                if (mode == "native") {
                    LlmService.start(this)
                }
                
                val intent = Intent(this, MemoryBridgeService::class.java).apply {
                    action = "START_RECORDING"
                }
                startService(intent)
                updateLoggerUI(true)
            }
        }

        btnManualRecap.setOnClickListener {
            Toast.makeText(this, "Manual 20->7 Curation Triggered via LLM", Toast.LENGTH_LONG).show()
            val intent = Intent(this, MemoryBridgeService::class.java).apply {
                action = "MANUAL_RECAP_TRIGGER"
            }
            startService(intent)
        }

        btnStopLogging.setOnClickListener {
            sharedPrefs.edit().putBoolean("is_recording", false).apply()
            val intent = Intent(this, MemoryBridgeService::class.java).apply {
                action = "STOP_RECORDING"
            }
            startService(intent)
            updateLoggerUI(false)
        }

        // Setup Fullscreen Preview Click listeners
        btnClosePreview.setOnClickListener {
            layoutFullscreenPreview.visibility = View.GONE
            selectedPreviewFile = null
        }

        btnDeletePreview.setOnClickListener {
            selectedPreviewFile?.let { file ->
                if (file.exists() && file.delete()) {
                    Toast.makeText(this, "Memory deleted successfully", Toast.LENGTH_SHORT).show()
                    layoutFullscreenPreview.visibility = View.GONE
                    selectedPreviewFile = null
                    // Refresh data in both tabs
                    loadAlbumData()
                    loadStoryboardData()
                } else {
                    Toast.makeText(this, "Failed to delete file", Toast.LENGTH_SHORT).show()
                }
            }
        }

        // Request permissions and initialize state
        requestStoragePermissions()
        checkServiceStatus()
        checkModelStatus()
        
        // Sync Initial UI state
        val isRecordingActive = sharedPrefs.getBoolean("is_recording", false)
        updateLoggerUI(isRecordingActive)

        // Select default starting tab (Storyboard)
        switchTab(0)
    }

    override fun onResume() {
        super.onResume()
        checkServiceStatus()
        checkModelStatus()
        // Refresh tabs data in case changes occurred in the background
        loadAlbumData()
        loadStoryboardData()
    }

    private fun checkServiceStatus() {
        val active = isAccessibilityServiceEnabled()
        if (active) {
            statusDot.setBackgroundColor(Color.parseColor("#10B981"))
            statusLabel.text = "ACTIVE"
            statusLabel.setTextColor(Color.parseColor("#10B981"))
        } else {
            statusDot.setBackgroundColor(Color.parseColor("#EF4444"))
            statusLabel.text = "INACTIVE"
            statusLabel.setTextColor(Color.parseColor("#EF4444"))
        }
    }

    private fun isAccessibilityServiceEnabled(): Boolean {
        val expectedComponentName = ComponentName(this, MemoryBridgeService::class.java)
        val enabledServicesSetting = Settings.Secure.getString(contentResolver, Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES) ?: return false
        val colonSplitter = TextUtils.SimpleStringSplitter(':')
        colonSplitter.setString(enabledServicesSetting)
        while (colonSplitter.hasNext()) {
            val componentNameString = colonSplitter.next()
            val enabledService = ComponentName.unflattenFromString(componentNameString)
            if (enabledService != null && enabledService == expectedComponentName) {
                return true
            }
        }
        return false
    }

    private fun updateLoggerUI(isRecording: Boolean) {
        val active = isAccessibilityServiceEnabled()
        if (isRecording) {
            if (active) {
                statusText.text = "Status: Logging Screen Memories..."
            } else {
                statusText.text = "Status: Logger Enabled (Waiting for Accessibility)"
            }
        } else {
            statusText.text = "Status: Suspended"
        }
    }

    private fun switchTab(tabIndex: Int) {
        // Reset navigation colors
        textTabSettings.setTextColor(Color.parseColor("#5E6677"))
        textTabAlbum.setTextColor(Color.parseColor("#5E6677"))
        textTabStoryboard.setTextColor(Color.parseColor("#5E6677"))

        indicatorTabSettings.visibility = View.INVISIBLE
        indicatorTabAlbum.visibility = View.INVISIBLE
        indicatorTabStoryboard.visibility = View.INVISIBLE

        tabSettingsLayout.visibility = View.GONE
        tabAlbumLayout.visibility = View.GONE
        tabStoryboardLayout.visibility = View.GONE

        when (tabIndex) {
            0 -> { // Storyboard Tab
                textTabStoryboard.setTextColor(Color.parseColor("#A78BFA"))
                indicatorTabStoryboard.visibility = View.VISIBLE
                tabStoryboardLayout.visibility = View.VISIBLE
                loadStoryboardData()
            }
            1 -> { // Album Tab
                textTabAlbum.setTextColor(Color.parseColor("#8B5CF6"))
                indicatorTabAlbum.visibility = View.VISIBLE
                tabAlbumLayout.visibility = View.VISIBLE
                loadAlbumData()
            }
            2 -> { // Settings Tab
                textTabSettings.setTextColor(Color.parseColor("#06B6D4"))
                indicatorTabSettings.visibility = View.VISIBLE
                tabSettingsLayout.visibility = View.VISIBLE
                checkServiceStatus()
            }
        }
    }

    // --- Tab 2: Album loading logic ---
    private fun loadAlbumData() {
        if (!checkStoragePermissions()) return
        
        Thread {
            val rawDir = File(baseDir, "raw")
            if (!rawDir.exists()) rawDir.mkdirs()
            
            val files = rawDir.listFiles()?.filter { it.extension == "png" }
                ?.sortedByDescending { it.lastModified() } ?: emptyList()
                
            runOnUiThread {
                textAlbumCount.text = "${files.size} screenshots"
                recyclerAlbum.adapter = AlbumAdapter(files)
            }
        }.start()
    }

    inner class AlbumAdapter(private val files: List<File>) : RecyclerView.Adapter<AlbumAdapter.ViewHolder>() {

        inner class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
            val imageView: ImageView = view.findViewById(R.id.img_album_item)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
            val view = LayoutInflater.from(parent.context).inflate(R.layout.item_album, parent, false)
            return ViewHolder(view)
        }

        override fun onBindViewHolder(holder: ViewHolder, position: Int) {
            val file = files[position]
            holder.imageView.load(file)
            
            holder.itemView.setOnClickListener {
                selectedPreviewFile = file
                imgFullscreenPreview.load(file)
                layoutFullscreenPreview.visibility = View.VISIBLE
            }
        }

        override fun getItemCount(): Int = files.size
    }

    // --- Tab 3: Storyboard loading logic ---
    private fun loadStoryboardData() {
        if (!checkStoragePermissions()) return

        Thread {
            val rawDir = File(baseDir, "raw")
            if (!rawDir.exists()) rawDir.mkdirs()

            // Target Yesterday
            val calendar = Calendar.getInstance()
            calendar.add(Calendar.DAY_OF_YEAR, -1)
            val yesterday = calendar.get(Calendar.DAY_OF_YEAR)
            val year = calendar.get(Calendar.YEAR)

            val allFiles = rawDir.listFiles()?.filter { it.extension == "png" } ?: emptyList()

            var storyboardFiles = allFiles.filter {
                val fileCal = Calendar.getInstance()
                fileCal.timeInMillis = it.lastModified()
                fileCal.get(Calendar.DAY_OF_YEAR) == yesterday && fileCal.get(Calendar.YEAR) == year
            }.sortedBy { it.lastModified() }

            var isFallback = false
            var fallbackDateString = ""

            // Fallback: If yesterday has no memories, get the most recent day containing logs
            if (storyboardFiles.isEmpty() && allFiles.isNotEmpty()) {
                val mostRecentFile = allFiles.maxByOrNull { it.lastModified() }
                if (mostRecentFile != null) {
                    isFallback = true
                    val fileCal = Calendar.getInstance()
                    fileCal.timeInMillis = mostRecentFile.lastModified()
                    val targetDay = fileCal.get(Calendar.DAY_OF_YEAR)
                    val targetYear = fileCal.get(Calendar.YEAR)

                    storyboardFiles = allFiles.filter {
                        val cal = Calendar.getInstance()
                        cal.timeInMillis = it.lastModified()
                        cal.get(Calendar.DAY_OF_YEAR) == targetDay && cal.get(Calendar.YEAR) == targetYear
                    }.sortedBy { it.lastModified() }

                    val sdf = SimpleDateFormat("MMM dd, yyyy", Locale.getDefault())
                    fallbackDateString = sdf.format(Date(mostRecentFile.lastModified()))
                }
            }

            // Group files by package name, apply Gemma curation (selected_indices + summary)
            // from metadata/<pkg>_recap.json when available. Falls back to first 7 frames.
            val metadataDir = File(baseDir, "metadata")
            val groupedByPackage = storyboardFiles.groupBy { getPackageNameFromFilename(it.name) }
            val appGroups = groupedByPackage.map { (pkgName, files) ->
                val appName = getAppDisplayName(pkgName)
                val sorted = files.sortedBy { it.lastModified() }

                var selected: List<File> = sorted.take(7)
                var summary = ""
                var isCurated = false

                val recapFile = File(metadataDir, "${pkgName}_recap.json")
                if (recapFile.exists()) {
                    try {
                        val text = recapFile.readText()
                        val json = org.json.JSONObject(text)
                        // Skip stale error blobs from old failed runs
                        if (!json.has("error")) {
                            val indicesJson = json.optJSONArray("selected_indices")
                            if (indicesJson != null && indicesJson.length() > 0) {
                                val pool = sorted.takeLast(20)
                                val picked = mutableListOf<File>()
                                for (i in 0 until indicesJson.length()) {
                                    val idx = indicesJson.optInt(i, -1)
                                    if (idx in pool.indices) picked.add(pool[idx])
                                }
                                if (picked.isNotEmpty()) {
                                    selected = picked.take(7)
                                    isCurated = true
                                }
                            }
                            summary = json.optString("summary", "")
                                .ifBlank { json.optString("app_summary", "") }
                        }
                    } catch (e: Exception) {
                        Log.w(TAG, "Recap parse failed for $pkgName: ${e.message}")
                    }
                }

                AppGroup(
                    appName = appName,
                    packageName = pkgName,
                    files = selected,
                    summary = summary,
                    isCurated = isCurated,
                )
            }.sortedBy { it.files.firstOrNull()?.lastModified() ?: 0L }

            runOnUiThread {
                if (isFallback) {
                    textStoryboardBannerLabel.text = "No logs for yesterday. Showing captures from $fallbackDateString"
                    layoutStoryboardBanner.visibility = View.VISIBLE
                } else {
                    layoutStoryboardBanner.visibility = View.GONE
                }

                recyclerStoryboard.adapter = StoryboardAppGroupAdapter(appGroups)
            }
        }.start()
    }

    data class AppGroup(
        val appName: String,
        val packageName: String,
        val files: List<File>,
        val summary: String = "",
        val isCurated: Boolean = false
    )

    inner class StoryboardAppGroupAdapter(private val groups: List<AppGroup>) : RecyclerView.Adapter<StoryboardAppGroupAdapter.ViewHolder>() {

        inner class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
            val textAppName: TextView = view.findViewById(R.id.group_app_name)
            val textScreenshotCount: TextView = view.findViewById(R.id.group_screenshot_count)
            val textGemmaSummary: TextView = view.findViewById(R.id.group_gemma_summary)
            val recyclerHorizontal: RecyclerView = view.findViewById(R.id.recycler_horizontal_screenshots)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
            val view = LayoutInflater.from(parent.context).inflate(R.layout.item_storyboard_app_group, parent, false)
            return ViewHolder(view)
        }

        override fun onBindViewHolder(holder: ViewHolder, position: Int) {
            val group = groups[position]
            holder.textAppName.text = group.appName
            holder.textScreenshotCount.text = if (group.isCurated) {
                "Gemma · ${group.files.size} of 20"
            } else {
                "${group.files.size} screenshots"
            }

            if (group.summary.isNotBlank()) {
                holder.textGemmaSummary.text = group.summary
                holder.textGemmaSummary.visibility = View.VISIBLE
            } else {
                holder.textGemmaSummary.visibility = View.GONE
            }

            holder.recyclerHorizontal.layoutManager = LinearLayoutManager(holder.itemView.context, LinearLayoutManager.HORIZONTAL, false)
            holder.recyclerHorizontal.adapter = StoryboardScreenshotAdapter(group.files)
        }

        override fun getItemCount(): Int = groups.size
    }

    inner class StoryboardScreenshotAdapter(private val files: List<File>) : RecyclerView.Adapter<StoryboardScreenshotAdapter.ViewHolder>() {

        inner class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
            val imgPreview: ImageView = view.findViewById(R.id.screenshot_preview)
            val viewTriggerIndicator: View = view.findViewById(R.id.view_trigger_indicator)
            val textTime: TextView = view.findViewById(R.id.text_screenshot_time)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
            val view = LayoutInflater.from(parent.context).inflate(R.layout.item_storyboard_screenshot, parent, false)
            return ViewHolder(view)
        }

        override fun onBindViewHolder(holder: ViewHolder, position: Int) {
            val file = files[position]
            holder.imgPreview.load(file)

            val timeText = formatCaptureTime(file.name)
            holder.textTime.text = timeText

            val isPeriodic = file.name.contains("_periodic_")
            if (isPeriodic) {
                holder.viewTriggerIndicator.setBackgroundColor(Color.parseColor("#06B6D4")) // Cyan for periodic
            } else {
                holder.viewTriggerIndicator.setBackgroundColor(Color.parseColor("#C084FC")) // Light purple for app switch
            }

            holder.itemView.setOnClickListener {
                selectedPreviewFile = file
                imgFullscreenPreview.load(file)
                layoutFullscreenPreview.visibility = View.VISIBLE
            }
        }

        override fun getItemCount(): Int = files.size

        private fun formatCaptureTime(filename: String): String {
            val cleanName = filename.removeSuffix(".png")
            val parts = cleanName.split("_")
            // Current format: <pkg>_<YYYYMMDD>_<HHMMSS>
            if (parts.size >= 3) {
                val timeStr = parts.last()
                if (timeStr.length == 6 && timeStr.all { it.isDigit() }) {
                    try {
                        val hh = timeStr.substring(0, 2).toInt()
                        val mm = timeStr.substring(2, 4)
                        val ss = timeStr.substring(4, 6)
                        val ampm = if (hh >= 12) "PM" else "AM"
                        val displayHh = if (hh == 0) 12 else if (hh > 12) hh - 12 else hh
                        return "$displayHh:$mm:$ss $ampm"
                    } catch (e: Exception) { /* ignore */ }
                }
            }
            return ""
        }
    }

    private fun getPackageNameFromFilename(filename: String): String {
        val cleanName = filename.removeSuffix(".png")
        // Legacy format: <prefix><pkg_with_underscores>_periodic_<ts>
        val triggers = listOf("_periodic_", "_app_switch_")
        for (trigger in triggers) {
            val triggerIdx = cleanName.indexOf(trigger)
            if (triggerIdx != -1 && triggerIdx > 7) {
                return cleanName.substring(7, triggerIdx).replace("_", ".")
            }
        }
        // Current format: <pkg.with.dots>_<YYYYMMDD>_<HHMMSS>
        val parts = cleanName.split("_")
        if (parts.size >= 3) {
            val date = parts[parts.size - 2]
            val time = parts[parts.size - 1]
            if (date.length == 8 && date.all { it.isDigit() } &&
                time.length == 6 && time.all { it.isDigit() }) {
                return parts.subList(0, parts.size - 2).joinToString("_")
            }
        }
        return "unknown"
    }

    private fun getAppDisplayName(packageName: String): String {
        if (packageName == "unknown") return "System/Unknown Screen"

        val lower = packageName.lowercase(Locale.getDefault())
        return when {
            lower.contains("whatsapp") -> "WhatsApp"
            lower.contains("amazon") -> "Amazon Shopping"
            lower.contains("tiktok") -> "TikTok"
            lower.contains("chrome") -> "Google Chrome"
            lower.contains("youtube") -> "YouTube"
            lower.contains("settings") -> "System Settings"
            lower.contains("gallery") || lower.contains("photos") -> "Photo Gallery"
            lower.contains("maps") -> "Google Maps"
            lower.contains("calendar") -> "Calendar"
            lower.contains("contacts") -> "Contacts"
            lower.contains("videomemory") -> "AetherLens Companion"
            else -> {
                val parts = packageName.split(".")
                if (parts.isNotEmpty()) {
                    parts.last().replaceFirstChar { if (it.isLowerCase()) it.titlecase(Locale.getDefault()) else it.toString() }
                } else {
                    packageName
                }
            }
        }
    }

    private fun checkModelStatus() {
        val modelDir = File(getExternalFilesDir(null), "models")
        if (!modelDir.exists()) modelDir.mkdirs()
        
        val modelFile = File(modelDir, ModelDownloader.DEFAULT_MODEL_FILE)
        if (modelFile.exists()) {
            val sizeMB = modelFile.length() / (1024 * 1024)
            textModelStatus.text = "Status: Model ready ($sizeMB MB)"
            textModelStatus.setTextColor(Color.parseColor("#10B981"))
            btnDownloadModel.text = "Model Downloaded"
            btnDownloadModel.isEnabled = false
            btnDownloadModel.alpha = 0.5f
        } else {
            val tmpFile = File(modelFile.absolutePath + ".tmp")
            if (tmpFile.exists()) {
                val progress = (tmpFile.length() * 100 / ModelDownloader.TOTAL_SIZE).toInt()
                textModelStatus.text = "Status: Download paused ($progress%)"
                btnDownloadModel.text = "Resume Download"
            } else {
                textModelStatus.text = "Status: Model not found"
                btnDownloadModel.text = "Download Gemma-4-E2B-it (2.4GB)"
            }
            textModelStatus.setTextColor(Color.parseColor("#949DB0"))
            btnDownloadModel.isEnabled = true
            btnDownloadModel.alpha = 1.0f
        }
    }

    private fun startModelDownload() {
        val modelDir = File(getExternalFilesDir(null), "models")
        if (!modelDir.exists()) modelDir.mkdirs()
        val targetFile = File(modelDir, ModelDownloader.DEFAULT_MODEL_FILE)

        btnDownloadModel.isEnabled = false
        btnDownloadModel.text = "Downloading..."
        progressModelDownload.visibility = View.VISIBLE
        progressModelDownload.progress = 0

        lifecycleScope.launch {
            val url = ModelDownloader.getDownloadUrl(
                ModelDownloader.DEFAULT_MODEL_ID,
                ModelDownloader.DEFAULT_COMMIT_HASH,
                ModelDownloader.DEFAULT_MODEL_FILE
            )

            val success = ModelDownloader.download(url, targetFile) { received, total ->
                val progress = (received * 100 / total).toInt()
                runOnUiThread {
                    progressModelDownload.progress = progress
                    textModelStatus.text = "Downloading: $progress% (${received / (1024 * 1024)}MB / ${total / (1024 * 1024)}MB)"
                }
            }

            if (success) {
                Toast.makeText(this@MainActivity, "Model downloaded successfully!", Toast.LENGTH_LONG).show()
            } else {
                Toast.makeText(this@MainActivity, "Download failed or paused", Toast.LENGTH_LONG).show()
            }
            
            progressModelDownload.visibility = View.GONE
            checkModelStatus()
        }
    }

    // --- Permissions Logic ---
    private fun checkStoragePermissions(): Boolean {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            return Environment.isExternalStorageManager()
        } else {
            val writePermission = ContextCompat.checkSelfPermission(this, Manifest.permission.WRITE_EXTERNAL_STORAGE)
            val readPermission = ContextCompat.checkSelfPermission(this, Manifest.permission.READ_EXTERNAL_STORAGE)
            return writePermission == PackageManager.PERMISSION_GRANTED && readPermission == PackageManager.PERMISSION_GRANTED
        }
    }

    private fun requestStoragePermissions() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            if (!Environment.isExternalStorageManager()) {
                try {
                    val intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION).apply {
                        data = Uri.parse("package:${packageName}")
                    }
                    startActivity(intent)
                    Toast.makeText(this, "Grant All Files Access to save high-fidelity screen memories", Toast.LENGTH_LONG).show()
                } catch (e: Exception) {
                    val intent = Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION)
                    startActivity(intent)
                }
            }
        } else {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.WRITE_EXTERNAL_STORAGE, Manifest.permission.READ_EXTERNAL_STORAGE),
                PERMISSION_REQUEST_CODE
            )
        }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == PERMISSION_REQUEST_CODE) {
            if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                Toast.makeText(this, "Permissions granted! Ready to log screen memories.", Toast.LENGTH_SHORT).show()
                loadAlbumData()
                loadStoryboardData()
            } else {
                Toast.makeText(this, "Storage access is required to write screen storyboard frame files", Toast.LENGTH_LONG).show()
            }
        }
    }
}
