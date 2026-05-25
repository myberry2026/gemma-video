document.addEventListener("DOMContentLoaded", () => {
  // UI State
  let recapData = null;
  let activeAppId = "tiktok"; // Default starting app
  let activeFrameIndex = 0;   // Default starting frame

  // DOM Elements
  const activeDateDisplay = document.getElementById("active-date");
  const dailySummaryPara = document.getElementById("daily-summary-paragraph");
  const timelineWrapper = document.getElementById("timeline-items-wrapper");
  const filterNavigation = document.getElementById("filter-navigation");
  
  // Visualizer elements
  const activeAppName = document.getElementById("active-app-name");
  const activeAppTimestamp = document.getElementById("active-app-timestamp");
  const activeAppIcon = document.getElementById("active-app-icon");
  const activeAppSummaryContainer = document.getElementById("active-app-summary-container");
  const activeAppSummaryText = document.getElementById("active-app-summary-text");
  const scoreText = document.getElementById("score-text");
  const scoreCirclePath = document.getElementById("score-circle-path");
  const activeScreenshotImg = document.getElementById("active-screenshot-img");
  const activeAppDescription = document.getElementById("active-app-description");
  const activeAppOcr = document.getElementById("active-app-ocr");
  
  // Details tabs
  const tabDesc = document.getElementById("tab-desc");
  const tabOcr = document.getElementById("tab-ocr");
  const tabContentDesc = document.getElementById("detail-content-description");
  const tabContentOcr = document.getElementById("detail-content-ocr");
  
  // Fullscreen modal
  const screenshotContainer = document.getElementById("active-screenshot-container");
  const fullscreenModal = document.getElementById("fullscreen-modal");
  const modalLargeImg = document.getElementById("modal-large-img");
  const modalCloseBtn = document.getElementById("modal-close-btn");

  // SVG Icons Helper
  const getIconSvg = (iconName, color = "currentColor") => {
    const icons = {
      video: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m22 8-6 4 6 4V8Z"/><rect x="2" y="6" width="12" height="12" rx="2" ry="2"/></svg>`,
      shopping: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>`,
      message: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`,
      reddit: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 8a2 2 0 1 0-4 0v4a2 2 0 0 0 4 0v-4Z"/><path d="M16 12a2 2 0 1 0-4 0v4a2 2 0 0 0 4 0v-4Z"/></svg>`
    };
    return icons[iconName] || icons.video;
  };

  // Configuration
  let DEVICE_IP = localStorage.getItem("aetherlens_device_ip") || "";
  const deviceIpInput = document.getElementById("device-ip-input");
  const connectBtn = document.getElementById("connect-btn");
  const statusBadge = document.getElementById("recording-status-badge");
  const remoteControls = document.getElementById("remote-controls");
  const apiStartBtn = document.getElementById("api-start-btn");
  const apiStopBtn = document.getElementById("api-stop-btn");
  const apiRefineBtn = document.getElementById("api-refine-btn");

  if (deviceIpInput) {
    deviceIpInput.value = DEVICE_IP;
    connectBtn.addEventListener("click", () => {
      DEVICE_IP = deviceIpInput.value.trim();
      localStorage.setItem("aetherlens_device_ip", DEVICE_IP);
      fetchRecapData();
      startStatusPolling();
    });
  }

  // Remote Control Handlers
  apiStartBtn.onclick = () => sendControl("start");
  apiStopBtn.onclick = () => sendControl("stop");
  apiRefineBtn.onclick = () => triggerRefinement();

  async function sendControl(action) {
    if (!DEVICE_IP) return;
    try {
      const res = await fetch(`http://${DEVICE_IP}:9085/control?action=${action}`, { method: 'POST' });
      if (res.ok) updateStatusUI();
    } catch (e) { console.error("Control failed", e); }
  }

  async function triggerRefinement() {
    if (!DEVICE_IP) return;
    try {
      apiRefineBtn.textContent = "CURATING...";
      apiRefineBtn.disabled = true;
      const res = await fetch(`http://${DEVICE_IP}:9085/refine`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        alert(data.message || "Refinement started!");
      }
    } catch (e) { 
      console.error("Refinement failed", e); 
      alert("Failed to trigger refinement. Check connection.");
    } finally {
      apiRefineBtn.textContent = "REFINE (20->7)";
      apiRefineBtn.disabled = false;
    }
  }

  function startStatusPolling() {
    updateStatusUI();
    setInterval(updateStatusUI, 5000);
  }

  async function updateStatusUI() {
    if (!DEVICE_IP) return;
    try {
      const res = await fetch(`http://${DEVICE_IP}:9085/status`);
      if (res.ok) {
        const data = await res.json();
        statusBadge.style.display = "flex";
        remoteControls.style.display = "flex";
        const dot = statusBadge.querySelector(".status-dot");
        const text = statusBadge.querySelector(".status-text");
        
        if (data.isRecording) {
          dot.style.background = "#00E676";
          text.textContent = "RECORDING";
          statusBadge.style.background = "rgba(0, 230, 118, 0.1)";
          statusBadge.style.color = "#00E676";
        } else {
          dot.style.background = "#FF4500";
          text.textContent = "SUSPENDED";
          statusBadge.style.background = "rgba(255, 69, 0, 0.1)";
          statusBadge.style.color = "#FF4500";
        }
      }
    } catch (e) {
      statusBadge.style.display = "none";
      remoteControls.style.display = "none";
    }
  }

  if (DEVICE_IP) startStatusPolling();

  const USE_REMOTE_API = true;

  // Fetch JSON Daily Recap Report
  async function fetchRecapData() {
    try {
      if (USE_REMOTE_API && DEVICE_IP) {
        console.log(`[*] Attempting to fetch live memories from ${DEVICE_IP}...`);
        const response = await fetch(`http://${DEVICE_IP}:9085/memories`);
        if (!response.ok) throw new Error("Remote API unreachable");
        const files = await response.json();
        recapData = transformApiDataToRecap(files);
      } else {
        const response = await fetch("daily_recap.json");
        if (!response.ok) throw new Error("Recap report JSON not found.");
        recapData = await response.json();
      }

      if (recapData) {
        initDashboard();
      }
    } catch (error) {
      console.error("Error loading daily recap:", error);
      dailySummaryPara.textContent = "Error loading daily recap data. If using Remote API, ensure phone IP is set and phone is on the same WiFi.";
    }
  }

  // Transform flat file list from Ktor API into structured Recap format
  function transformApiDataToRecap(files) {
    const recap = {
      date: new Date().toISOString().split('T')[0],
      daily_recap_summary: `Live Session: Synchronized ${files.length} memory frames directly from your mobile device via AetherLens API.`,
      apps: {}
    };

    files.forEach(file => {
      // Pattern: Memory_package_name_trigger_timestamp.png
      const parts = file.name.split('_');
      if (parts.length < 4) return;
      
      const appKey = parts.slice(1, -2).join('_'); // Get package name part
      const timestampRaw = parts[parts.length - 2] + "_" + parts[parts.length - 1].split('.')[0];
      
      if (!recap.apps[appKey]) {
        recap.apps[appKey] = {
          name: appKey.split('_').pop().charAt(0).toUpperCase() + appKey.split('_').pop().slice(1),
          color: "#" + Math.floor(Math.random()*16777215).toString(16), // Random color for new apps
          icon: "video",
          usage_time: "Live",
          storyboard: []
        };
      }

      recap.apps[appKey].storyboard.push({
        image_path: `http://${DEVICE_IP}:9085${file.url}`,
        timestamp: timestampRaw,
        action: parts[parts.length - 3], // trigger type
        description: `Live capture from ${appKey}`,
        score: 85
      });
    });

    return recap;
  }

  // Initialize Dashboard Viewports
  function initDashboard() {
    // Set dynamic date
    if (recapData.date) {
      const parsedDate = new Date(recapData.date);
      const options = { month: 'long', day: 'numeric', year: 'numeric' };
      activeDateDisplay.textContent = parsedDate.toLocaleDateString('en-US', options);
    }
    
    // Set AI Summary block
    dailySummaryPara.textContent = recapData.daily_recap_summary;
    
    // Default active app key check
    const appKeys = Object.keys(recapData.apps);
    if (appKeys.length > 0) {
      activeAppId = appKeys[0];
    }
    
    setupFilterTabs();
    renderTimeline();
    renderActiveAppDetails();
  }

  // Setup Dynamic Filter Tabs based on Categories
  function setupFilterTabs() {
    if (!recapData || !recapData.apps) return;
    
    const categories = new Set();
    Object.values(recapData.apps).forEach(app => {
      if (app.category) categories.add(app.category);
    });

    filterNavigation.innerHTML = `
      <button class="filter-tab active" data-filter="all" id="filter-all">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
        All Memories
      </button>
    `;
    
    categories.forEach(cat => {
      const tab = document.createElement("button");
      tab.className = "filter-tab";
      tab.setAttribute("data-filter", cat);
      tab.innerHTML = `<span class="dot" style="background-color: #3B82F6;"></span> ${cat}`;
      filterNavigation.appendChild(tab);
    });

    // Wire up tab click listeners
    const tabs = filterNavigation.querySelectorAll(".filter-tab");
    tabs.forEach(tab => {
      tab.addEventListener("click", () => {
        tabs.forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        
        const filterValue = tab.getAttribute("data-filter");
        renderTimeline(filterValue);
      });
    });
  }

  // Render left column timeline items filtered by category
  function renderTimeline(filter = "all") {
    timelineWrapper.innerHTML = "";

    if (!recapData || !recapData.apps) return;

    const appsList = Object.entries(recapData.apps);
    let totalMinutes = 0;

    appsList.forEach(([appKey, app]) => {
      // Apply category filters
      if (filter !== "all" && app.category !== filter) return;

      totalMinutes += parseInt(app.usage_time) || 0;
  ...
      const storyboard = app.storyboard || [];
      const firstFrame = storyboard[0] || {};
      
      const timelineItem = document.createElement("div");
      timelineItem.className = `timeline-item ${appKey === activeAppId ? 'active' : ''}`;
      timelineItem.style.setProperty("--app-color", app.color);
      timelineItem.setAttribute("data-app-id", appKey);
      
      timelineItem.innerHTML = `
        <div class="timeline-time">${app.usage_time}</div>
        <div class="timeline-node-content">
          <span class="timeline-app-name">${app.name}</span>
          <span class="timeline-app-snippet">${firstFrame.description || firstFrame.action || "No details"}</span>
          <div class="timeline-meta">
            <span class="timeline-duration">${storyboard.length} frames</span>
            <span class="timeline-score-pill" style="color: ${app.color}; background: ${app.color}15;">
              Select
            </span>
          </div>
        </div>
      `;
      
      timelineItem.addEventListener("click", () => {
        activeAppId = appKey;
        activeFrameIndex = 0; // reset to first step
        
        document.querySelectorAll(".timeline-item").forEach(item => item.classList.remove("active"));
        timelineItem.classList.add("active");
        
        renderActiveAppDetails();
      });
      
      timelineWrapper.appendChild(timelineItem);
    });

    document.getElementById("total-usage-time").textContent = `Total: ${totalMinutes} mins`;
  }

  // Render right column selected App visualizer & storyboard slider
  function renderActiveAppDetails() {
    if (!recapData || !recapData.apps) return;
    
    const app = recapData.apps[activeAppId];
    if (!app) return;
    
    const storyboard = app.storyboard || [];
    const activeFrame = storyboard[activeFrameIndex] || {};
    
    // Set Header
    activeAppName.textContent = app.name;
    activeAppTimestamp.textContent = activeFrame.timestamp || "No time";
    activeAppIcon.innerHTML = getIconSvg(app.icon, app.color);
    activeAppIcon.style.borderColor = app.color + "40";
    activeAppIcon.style.background = app.color + "10";

    // Set App Summary
    if (app.summary) {
      activeAppSummaryContainer.style.display = "block";
      activeAppSummaryContainer.style.borderLeftColor = app.color;
      activeAppSummaryText.textContent = app.summary;
    } else {
      activeAppSummaryContainer.style.display = "none";
    }
    
    // Set Memorability Score
    const score = activeFrame.score || 80;
    scoreText.textContent = score;
    
    // Animate circular chart stroke
    const strokeDash = `${score}, 100`;
    scoreCirclePath.setAttribute("stroke-dasharray", strokeDash);
    scoreCirclePath.setAttribute("stroke", app.color);
    
    // Render main screenshot
    if (activeFrame.image_path) {
      activeScreenshotImg.src = activeFrame.image_path;
      activeScreenshotImg.alt = activeFrame.action || app.name;
    } else {
      activeScreenshotImg.src = "";
    }
    
    // Check if storyboard ribbon exists or create it
    let storyboardRibbon = document.getElementById("storyboard-ribbon");
    if (!storyboardRibbon) {
      storyboardRibbon = document.createElement("div");
      storyboardRibbon.id = "storyboard-ribbon";
      storyboardRibbon.className = "storyboard-ribbon-container";
      screenshotContainer.parentNode.insertBefore(storyboardRibbon, screenshotContainer.nextSibling);
    }
    
    storyboardRibbon.innerHTML = "";
    
    const ribbonTitle = document.createElement("div");
    ribbonTitle.className = "ribbon-header";
    ribbonTitle.innerHTML = `
      <span class="ribbon-title">Sequence Storyboard (ADB 5s Interval)</span>
      <span class="ribbon-steps">Frame ${activeFrameIndex + 1} of ${storyboard.length}</span>
    `;
    storyboardRibbon.appendChild(ribbonTitle);
    
    const cardsWrapper = document.createElement("div");
    cardsWrapper.className = "ribbon-cards-wrapper";
    
    storyboard.forEach((frame, idx) => {
      const card = document.createElement("div");
      card.className = `storyboard-card ${idx === activeFrameIndex ? 'active' : ''}`;
      card.style.setProperty("--app-color", app.color);
      
      card.innerHTML = `
        <div class="card-step-badge">${idx + 1}</div>
        <div class="card-thumb-container">
          <img src="${frame.image_path}" class="card-thumb-img" alt="step thumbnail">
        </div>
        <div class="card-details">
          <div class="card-action">Step ${idx + 1}</div>
          <div class="card-time">${frame.score || 80} pts</div>
        </div>
      `;
      
      card.addEventListener("click", () => {
        activeFrameIndex = idx;
        renderActiveAppDetails();
      });
      
      cardsWrapper.appendChild(card);
    });
    
    storyboardRibbon.appendChild(cardsWrapper);
    
    // Dynamic Gemma-4 Selection reasoning card
    let gemmaReasoningCard = document.getElementById("gemma-reasoning-card");
    if (app.reasoning) {
      if (!gemmaReasoningCard) {
        gemmaReasoningCard = document.createElement("div");
        gemmaReasoningCard.id = "gemma-reasoning-card";
        gemmaReasoningCard.className = "gemma-reasoning-glow-box";
        storyboardRibbon.parentNode.insertBefore(gemmaReasoningCard, storyboardRibbon.nextSibling);
      }
      gemmaReasoningCard.style.display = "block";
      gemmaReasoningCard.innerHTML = `
        <div class="gemma-card-header">
          <svg class="sparkle-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#a78bfa" stroke-width="2"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/></svg>
          <span>GEMMA-4 CURATION REASONING</span>
        </div>
        <p class="gemma-card-text">
          ${app.reasoning}
        </p>
      `;
    } else {
      if (gemmaReasoningCard) {
        gemmaReasoningCard.style.display = "none";
      }
    }
    
    // Set text details
    activeAppDescription.textContent = activeFrame.description || "No detail description available for this frame.";
    activeAppOcr.textContent = `Timestamp: ${activeFrame.timestamp}\nAction: ${activeFrame.action}\nScore: ${score} / 100\n\nApp Detail:\n${activeFrame.description}`;
  }

  // Visualizer details tab toggle (Gemma vs OCR)
  tabDesc.addEventListener("click", () => {
    tabDesc.classList.add("active");
    tabOcr.classList.remove("active");
    tabContentDesc.classList.add("active");
    tabContentOcr.classList.remove("active");
  });

  tabOcr.addEventListener("click", () => {
    tabOcr.classList.add("active");
    tabDesc.classList.remove("active");
    tabContentOcr.classList.add("active");
    tabContentDesc.classList.remove("active");
  });

  // Fullscreen Zoom modal features
  screenshotContainer.addEventListener("click", () => {
    if (activeScreenshotImg.src) {
      modalLargeImg.src = activeScreenshotImg.src;
      fullscreenModal.classList.add("active");
    }
  });

  const closeModal = () => {
    fullscreenModal.classList.remove("active");
  };

  modalCloseBtn.addEventListener("click", closeModal);
  fullscreenModal.addEventListener("click", (e) => {
    if (e.target === fullscreenModal) closeModal();
  });
  
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModal();
  });

  // Start data fetch
  fetchRecapData();
});
