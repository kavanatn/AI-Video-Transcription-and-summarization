document.addEventListener('DOMContentLoaded', () => {
    // Check which page we are on
    if (document.getElementById('drop-zone')) {
        initIndexPage();
    } else if (document.getElementById('result-container')) {
        initResultPage();
    }
});

// --- Index Page Logic ---
function initIndexPage() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const urlBtn = document.getElementById('url-btn');
    const urlInput = document.getElementById('url-input');

    // Drag & Drop
    dropZone.addEventListener('click', () => fileInput.click());
    
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('bg-dark-subtle');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('bg-dark-subtle');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('bg-dark-subtle');
        if (e.dataTransfer.files.length) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) {
            handleFileUpload(fileInput.files[0]);
        }
    });

    // URL Processing
    urlBtn.addEventListener('click', () => {
        const url = urlInput.value.trim();
        if (url) {
            handleUrlProcess(url);
        }
    });
}

function showProgress() {
    document.getElementById('progress-section').classList.remove('d-none');
    document.querySelector('.glass-panel').classList.add('d-none'); // Hide input panel
}

function updateProgress(status, progress, message) {
    document.getElementById('progress-status').innerText = status.toUpperCase();
    document.getElementById('progress-detail').innerText = message;
    document.getElementById('progress-bar').style.width = progress + '%';
}

function handleFileUpload(file) {
    showProgress();
    const formData = new FormData();
    formData.append('file', file);

    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        if (data.job_id) {
            pollStatus(data.job_id);
        } else {
            alert('Upload failed: ' + (data.error || 'Unknown error'));
            location.reload();
        }
    })
    .catch(e => {
        alert('Error: ' + e);
        location.reload();
    });
}

function handleUrlProcess(url) {
    showProgress();
    fetch('/process-url', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({url: url})
    })
    .then(r => r.json())
    .then(data => {
        if (data.job_id) {
            pollStatus(data.job_id);
        } else {
            alert('Processing failed: ' + (data.error || 'Unknown error'));
            location.reload();
        }
    })
    .catch(e => {
        alert('Error: ' + e);
        location.reload();
    });
}

function pollStatus(jobId) {
    const interval = setInterval(() => {
        fetch(`/status/${jobId}`)
        .then(r => r.json())
        .then(status => {
            updateProgress(status.status, status.progress, status.message);
            if (status.status === 'completed') {
                clearInterval(interval);
                window.location.href = `/result/${jobId}`;
            } else if (status.status === 'failed') {
                clearInterval(interval);
                alert('Job failed: ' + status.message);
                location.reload();
            }
        });
    }, 2000); // Poll every 2 seconds
}

// --- Result Page Logic ---
let currentTranscript = [];

function initResultPage() {
    const container = document.getElementById('result-container');
    const jobId = container.dataset.jobId;

    if (!jobId) return;

    // Load Data
    fetch(`/api/result/${jobId}`)
    .then(r => r.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
            return;
        }
        renderResult(data);
    })
    .catch(e => console.error(e));

    // Event Listeners
    document.getElementById('search-input').addEventListener('input', (e) => {
        filterTranscript(e.target.value);
    });

    document.getElementById('btn-download-pdf').addEventListener('click', () => {
        window.location.href = `/download/pdf/${jobId}`;
    });

    document.getElementById('btn-download-srt').addEventListener('click', () => {
        window.location.href = `/download/srt/${jobId}`;
    });
    
    // Translation Listener
    // Note: The button has onclick="translateSummary()" in HTML, 
    // so we must expose this function globally or attach listener here if we remove onclick.
    // For safety, let's attach listener via ID and also expose it just in case.
    const translateBtn = document.getElementById('translateBtn');
    if (translateBtn) {
         translateBtn.addEventListener('click', translateSummary);
    }
}

function renderResult(data) {
    // Hide loading, show content
    document.getElementById('loading-state').classList.add('d-none');
    document.getElementById('content-row').classList.remove('d-none');

    // Summary
    document.getElementById('summary-content').innerText = data.summary || "No summary available.";

    // Sentiment
    if (data.sentiment) {
        document.getElementById('sentiment-pos').innerText = (data.sentiment.pos * 100).toFixed(0) + '%';
        document.getElementById('sentiment-neu').innerText = (data.sentiment.neu * 100).toFixed(0) + '%';
        document.getElementById('sentiment-neg').innerText = (data.sentiment.neg * 100).toFixed(0) + '%';
    }

    // Transcript
    currentTranscript = data.transcript || [];
    renderTranscriptItems(currentTranscript);

    // Chapters
    if (data.chapters) {
        renderChapters(data.chapters);
    }
}

function renderChapters(chapters) {
    const list = document.getElementById('chapters-list');
    list.innerHTML = '';

    if (!chapters || chapters.length === 0) {
        list.innerHTML = '<span class="text-muted small text-center">No chapters generated.</span>';
        return;
    }

    chapters.forEach(chap => {
        const item = document.createElement('a');
        item.href = "#";
        item.className = 'list-group-item list-group-item-action bg-transparent text-light border-secondary d-flex justify-content-between align-items-start py-2 px-1';
        
        item.innerHTML = `
            <div class="ms-2 me-auto">
                <div class="fw-bold small text-info">${chap.title}</div>
                <small class="text-muted" style="font-size: 0.75rem;">${formatTime(chap.start)} - ${formatTime(chap.end)}</small>
            </div>
            <i class="bi bi-play-circle text-secondary"></i>
        `;
        
        item.addEventListener('click', (e) => {
            e.preventDefault();
            // Scroll transcript to this time
            scrollToTime(chap.start);
        });

        list.appendChild(item);
    });
}

function scrollToTime(seconds) {
    // Find the transcript item closest to this time
    // We can assume transcript is sorted or just find first item >= time
    // But items format is {start, end, text...}
    // We need to access DOM elements.
    // Let's re-render or just find the element?
    // Since we render all items, we can try to find the match in DOM.
    // Ideally we should add data-start attribute to transcript items.
    
    // For now, let's find it by iterating our currentTranscript data to find index
    // then finding the nth child.
    const idx = currentTranscript.findIndex(t => t.start >= seconds);
    if (idx !== -1) {
        const container = document.getElementById('transcript-content');
        const target = container.children[idx];
        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'center' });
            // Highlight effect
            target.classList.add('bg-dark-subtle');
            setTimeout(() => target.classList.remove('bg-dark-subtle'), 2000);
        }
    }
}

function renderTranscriptItems(items) {
    const container = document.getElementById('transcript-content');
    container.innerHTML = '';

    if (items.length === 0) {
        container.innerHTML = '<p class="text-muted text-center mt-5">No transcript data.</p>';
        return;
    }

    items.forEach(item => {
        const div = document.createElement('div');
        div.className = 'transcript-item mb-3 p-3 border border-secondary rounded glass-panel-sm';
        
        const time = formatTime(item.start);
        const speaker = item.speaker || 'Speaker';
        
        // Colorize speakers randomly or deterministically? 
        // For now just simple text.
        
        div.innerHTML = `
            <div class="d-flex justify-content-between text-muted small mb-1">
                <span class="fw-bold text-info">${speaker}</span>
                <span>${time}</span>
            </div>
            <p class="mb-0 text-light">${item.text}</p>
        `;
        container.appendChild(div);
    });
}

function formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

function filterTranscript(query) {
    if (!query) {
        renderTranscriptItems(currentTranscript);
        return;
    }
    const lowerQ = query.toLowerCase();
    const filtered = currentTranscript.filter(item => 
        item.text.toLowerCase().includes(lowerQ) || 
        (item.speaker && item.speaker.toLowerCase().includes(lowerQ))
    );
    renderTranscriptItems(filtered);
}

// Global for onclick attribute
window.translateSummary = function() {
    const btn = document.getElementById('translateBtn');
    const loading = document.getElementById('translationLoading');
    const select = document.getElementById('summaryLanguage');
    const summaryEl = document.getElementById('summary-content');

    const targetLang = select.value;
    const currentSummary = summaryEl.innerText;

    if (!targetLang) {
        alert("Please select a language.");
        return;
    }

    // UI Loading State
    btn.disabled = true;
    loading.classList.remove('d-none');

    fetch('/api/translate-summary', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            summary: currentSummary,
            target_lang: targetLang
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            summaryEl.innerText = data.translated_summary;
        } else {
            alert("Translation failed: " + data.error);
        }
    })
    .catch(e => {
        alert("Network error: " + e);
    })
    .finally(() => {
        btn.disabled = false;
        loading.classList.add('d-none');
    });
};
