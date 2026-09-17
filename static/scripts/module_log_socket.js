// ./static/scripts/module_log_socket.js

document.addEventListener("DOMContentLoaded", () => {
    const socket = io();
    const moduleName = window.LEAM_MODULE;
    if (!moduleName) return;

    const logsContainer = document.getElementById("logs-content");
    const resumeScrollBtn = document.getElementById("resume-scroll-btn");
    const filterInput = document.getElementById("log-filter-input");
    const copyBtn = document.getElementById("copy-logs-btn");
    const clearBtn = document.getElementById("clear-logs-btn");
    const lineCountEl = document.getElementById("log-line-count");
    const streamStatusEl = document.getElementById("stream-status-dot");
    const streamStatusText = document.getElementById("stream-status-text");

    if (!logsContainer) return;

    const MAX_LOGS = 3000;
    const logBuffer = []; // stores raw line strings
    let autoScrollEnabled = true;
    let isUserScrolledUp = false;
    let activeFilter = "";

    // Helper: format and categorize log line
    function parseLogLine(rawLine) {
        const text = rawLine || "";
        let level = "INFO";
        let timestamp = "";
        let message = text;

        // Match format: 2026-09-17 08:41:03 | LEVEL | message
        const match = text.match(/^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s*\|\s*([A-Z]+)\s*\|\s*(.*)$/);
        if (match) {
            timestamp = match[1];
            level = match[2];
            message = match[3];
        } else if (text.includes("--- SUPERVISOR START") || text.includes("--- FINISHED")) {
            level = "SYSTEM";
        } else if (/error|exception|fail|traceback/i.test(text)) {
            level = "ERROR";
        } else if (/warn/i.test(text)) {
            level = "WARN";
        } else if (/success|completed|rendered/i.test(text)) {
            level = "SUCCESS";
        }

        return { timestamp, level, message, raw: text };
    }

    // Helper: create a DOM element for a log line
    function createLogElement(parsed, index) {
        const lineEl = document.createElement("div");
        lineEl.className = `terminal-line level-${parsed.level.toLowerCase()}`;
        lineEl.setAttribute("data-index", index);

        if (activeFilter && !parsed.raw.toLowerCase().includes(activeFilter)) {
            lineEl.classList.add("hidden-line");
        }

        // Line number
        const numSpan = document.createElement("span");
        numSpan.className = "line-num";
        numSpan.textContent = index + 1;

        // Content
        const contentSpan = document.createElement("span");
        contentSpan.className = "line-content";

        if (parsed.timestamp) {
            const timeSpan = document.createElement("span");
            timeSpan.className = "line-time";
            timeSpan.textContent = parsed.timestamp.slice(11); // HH:MM:SS
            contentSpan.appendChild(timeSpan);
        }

        const badgeSpan = document.createElement("span");
        badgeSpan.className = `line-badge badge-${parsed.level.toLowerCase()}`;
        badgeSpan.textContent = parsed.level;
        contentSpan.appendChild(badgeSpan);

        const msgSpan = document.createElement("span");
        msgSpan.className = "line-msg";
        msgSpan.textContent = parsed.message;
        contentSpan.appendChild(msgSpan);

        lineEl.appendChild(numSpan);
        lineEl.appendChild(contentSpan);
        return lineEl;
    }

    function updateLineCount() {
        if (lineCountEl) {
            lineCountEl.textContent = `${logBuffer.length} lines`;
        }
    }

    function checkScrollPosition() {
        const scrollDistance = logsContainer.scrollHeight - logsContainer.scrollTop - logsContainer.clientHeight;
        // If user is within 50px of bottom, consider it at the bottom
        if (scrollDistance > 50) {
            isUserScrolledUp = true;
            if (resumeScrollBtn) resumeScrollBtn.style.display = "flex";
        } else {
            isUserScrolledUp = false;
            if (resumeScrollBtn) resumeScrollBtn.style.display = "none";
        }
    }

    function scrollToBottom(force = false) {
        if (!force && (!autoScrollEnabled || isUserScrolledUp)) {
            return;
        }
        logsContainer.scrollTop = logsContainer.scrollHeight;
        isUserScrolledUp = false;
        if (resumeScrollBtn) resumeScrollBtn.style.display = "none";
    }

    // Scroll listener on container
    logsContainer.addEventListener("scroll", () => {
        checkScrollPosition();
    });

    // Resume scroll button click
    if (resumeScrollBtn) {
        resumeScrollBtn.addEventListener("click", () => {
            isUserScrolledUp = false;
            scrollToBottom(true);
        });
    }

    // Render bulk lines (from existing_logs)
    function renderBulkLogs(lines) {
        logsContainer.innerHTML = "";
        logBuffer.length = 0;

        const fragment = document.createDocumentFragment();
        const start = Math.max(0, lines.length - MAX_LOGS);
        const slice = lines.slice(start);

        slice.forEach((rawLine) => {
            logBuffer.push(rawLine);
            const parsed = parseLogLine(rawLine);
            fragment.appendChild(createLogElement(parsed, logBuffer.length - 1));
        });

        logsContainer.appendChild(fragment);
        updateLineCount();
        scrollToBottom(true);
    }

    // Append single incoming line
    function appendLog(rawLine) {
        if (!rawLine || !rawLine.trim()) return;

        // Push to buffer
        logBuffer.push(rawLine);
        if (logBuffer.length > MAX_LOGS) {
            logBuffer.shift();
            // remove first child
            if (logsContainer.firstElementChild) {
                logsContainer.removeChild(logsContainer.firstElementChild);
            }
        }

        const parsed = parseLogLine(rawLine);
        const el = createLogElement(parsed, logBuffer.length - 1);
        logsContainer.appendChild(el);

        updateLineCount();
        scrollToBottom();

        // Flash status
        if (streamStatusEl) {
            streamStatusEl.classList.add("active-pulse");
            clearTimeout(window._streamTimer);
            window._streamTimer = setTimeout(() => {
                streamStatusEl.classList.remove("active-pulse");
            }, 800);
        }
    }

    // Subscribe to module logs
    socket.emit("subscribe_logs", { module: moduleName });

    // Batch historic logs
    socket.on("existing_logs", (data) => {
        if (data.module !== moduleName) return;
        if (Array.isArray(data.lines)) {
            renderBulkLogs(data.lines);
        }
    });

    // Real-time log line
    socket.on("module_log", (data) => {
        if (data.module !== moduleName) return;
        appendLog(data.line);
    });

    // Status updates
    socket.on("module_status", (data) => {
        if (data.module !== moduleName) return;
        if (data.status === "running") {
            if (streamStatusEl) streamStatusEl.classList.add("online");
            if (streamStatusText) streamStatusText.textContent = "LIVE";
        } else {
            if (streamStatusEl) streamStatusEl.classList.remove("online");
            if (streamStatusText) streamStatusText.textContent = "IDLE";
        }
    });

    // Filter logs
    if (filterInput) {
        filterInput.addEventListener("input", (e) => {
            activeFilter = e.target.value.trim().toLowerCase();
            const lines = logsContainer.querySelectorAll(".terminal-line");
            lines.forEach((line) => {
                const text = line.textContent.toLowerCase();
                if (!activeFilter || text.includes(activeFilter)) {
                    line.classList.remove("hidden-line");
                } else {
                    line.classList.add("hidden-line");
                }
            });
        });
    }

    // Copy logs
    if (copyBtn) {
        copyBtn.addEventListener("click", () => {
            const textToCopy = logBuffer.join("\n");
            navigator.clipboard.writeText(textToCopy).then(() => {
                const original = copyBtn.innerHTML;
                copyBtn.innerHTML = `<span>✓ Copied!</span>`;
                setTimeout(() => {
                    copyBtn.innerHTML = original;
                }, 2000);
            }).catch(() => {
                alert("Failed to copy logs to clipboard.");
            });
        });
    }

    // Clear view
    if (clearBtn) {
        clearBtn.addEventListener("click", () => {
            logsContainer.innerHTML = "";
            logBuffer.length = 0;
            updateLineCount();
        });
    }
});
