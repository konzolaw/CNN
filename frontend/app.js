// DOM Elements
const searchDropzone = document.getElementById('search-dropzone');
const searchFileInput = document.getElementById('search-file-input');
const searchDropzonePrompt = document.getElementById('search-dropzone-prompt');
const searchPreviewContainer = document.getElementById('search-preview-container');
const searchPreviewImage = document.getElementById('search-preview-image');
const clearSearchBtn = document.getElementById('clear-search-btn');

const webcamToggleBtn = document.getElementById('webcam-toggle-btn');
const webcamContainer = document.getElementById('webcam-container');
const webcamVideo = document.getElementById('webcam-video');
const webcamCanvas = document.getElementById('webcam-canvas');
const webcamCaptureBtn = document.getElementById('webcam-capture-btn');
const webcamCloseBtn = document.getElementById('webcam-close-btn');

const resultsCount = document.getElementById('results-count');
const searchLoading = document.getElementById('search-loading');
const resultsGrid = document.getElementById('results-grid');

const galleryGrid = document.getElementById('gallery-grid');
const galleryLoading = document.getElementById('gallery-loading');
const galleryUploadBtn = document.getElementById('gallery-upload-btn');
const galleryFileInput = document.getElementById('gallery-file-input');

const toast = document.getElementById('toast');
const toastMessage = document.getElementById('toast-message');

let webcamStream = null;

// ----------------------------------------------------
// Toast Notification Utility
// ----------------------------------------------------
function showToast(message) {
    toastMessage.textContent = message;
    toast.classList.remove('hidden');
    
    // Auto hide after 3.5s
    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3500);
}

// ----------------------------------------------------
// UI State Modifiers
// ----------------------------------------------------
function showSearchLoading(isLoading) {
    if (isLoading) {
        searchLoading.classList.remove('hidden');
        resultsGrid.classList.add('hidden');
        resultsCount.textContent = "Processing query...";
    } else {
        searchLoading.classList.add('hidden');
        resultsGrid.classList.remove('hidden');
    }
}

function showGalleryLoading(isLoading) {
    if (isLoading) {
        galleryLoading.classList.remove('hidden');
        galleryGrid.classList.add('hidden');
    } else {
        galleryLoading.classList.add('hidden');
        galleryGrid.classList.remove('hidden');
    }
}

function showQueryPreview(imgSrc) {
    searchPreviewImage.src = imgSrc;
    searchPreviewContainer.classList.remove('hidden');
    searchDropzonePrompt.classList.add('hidden');
}

function resetQueryPreview() {
    searchPreviewImage.src = '';
    searchPreviewContainer.classList.add('hidden');
    searchDropzonePrompt.classList.remove('hidden');
    searchFileInput.value = '';
    
    // Reset results grid
    resultsGrid.innerHTML = `
        <div class="placeholder-card">
            <div class="placeholder-icon"><i class="fa-regular fa-image"></i></div>
            <p>Awaiting query image</p>
        </div>
    `;
    resultsCount.textContent = "Results will appear here once search completes.";
}

// ----------------------------------------------------
// Core API Calls
// ----------------------------------------------------

// Fetch gallery images
async function loadGallery() {
    showGalleryLoading(true);
    try {
        const response = await fetch('/api/gallery');
        if (!response.ok) throw new Error('Failed to load gallery');
        const data = await response.json();
        renderGallery(data.images);
    } catch (error) {
        console.error(error);
        showToast('Error loading image gallery.');
    } finally {
        showGalleryLoading(false);
    }
}

// Perform semantic search
async function performSearch(file) {
    showSearchLoading(true);
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || 'Search request failed');
        }
        
        const data = await response.json();
        renderResults(data.results);
    } catch (error) {
        console.error(error);
        showToast(`Search failed: ${error.message}`);
        resetQueryPreview();
    } finally {
        showSearchLoading(false);
    }
}

// Search using an existing gallery image
async function searchWithGalleryImage(filename) {
    showSearchLoading(true);
    try {
        // Show local loading state immediately
        const imageUrl = `/gallery/${filename}`;
        showQueryPreview(imageUrl);
        
        // Fetch file blob, convert to File object, and perform search
        const response = await fetch(imageUrl);
        const blob = await response.blob();
        const file = new File([blob], filename, { type: blob.type });
        
        await performSearch(file);
    } catch (error) {
        console.error(error);
        showToast(`Failed to search using gallery image: ${error.message}`);
        showSearchLoading(false);
    }
}

// Upload new image to gallery
async function uploadToGallery(files) {
    showGalleryLoading(true);
    let successCount = 0;
    
    for (let i = 0; i < files.length; i++) {
        const formData = new FormData();
        formData.append('file', files[i]);
        
        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            if (response.ok) successCount++;
        } catch (error) {
            console.error(`Upload error for ${files[i].name}:`, error);
        }
    }
    
    if (successCount > 0) {
        showToast(`Successfully added ${successCount} image(s) to the database.`);
        await loadGallery();
    } else {
        showToast('Failed to upload images.');
        showGalleryLoading(false);
    }
}

// Delete image from database
async function deleteGalleryImage(filename, event) {
    event.stopPropagation(); // Avoid triggering search when clicking delete
    
    if (!confirm(`Are you sure you want to delete ${filename} from the database?`)) {
        return;
    }
    
    showGalleryLoading(true);
    try {
        const response = await fetch(`/api/gallery/${filename}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showToast(`Deleted ${filename} from database.`);
            await loadGallery();
        } else {
            throw new Error('Delete request failed');
        }
    } catch (error) {
        console.error(error);
        showToast(`Failed to delete image: ${error.message}`);
        showGalleryLoading(false);
    }
}

// ----------------------------------------------------
// UI Renderers
// ----------------------------------------------------

function renderGallery(images) {
    galleryGrid.innerHTML = '';
    
    if (images.length === 0) {
        galleryGrid.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 40px;">
                <i class="fa-regular fa-folder-open" style="font-size: 32px; margin-bottom: 8px;"></i>
                <p>The database is empty. Upload some images to get started!</p>
            </div>
        `;
        return;
    }
    
    images.forEach(img => {
        const card = document.createElement('div');
        card.className = 'gallery-card';
        card.addEventListener('click', () => searchWithGalleryImage(img.filename));
        
        card.innerHTML = `
            <div class="gallery-img-wrapper">
                <img src="${img.url}" alt="${img.filename}" loading="lazy">
            </div>
            <div class="gallery-card-overlay">
                <button class="btn btn-danger btn-circle delete-btn" title="Delete image">
                    <i class="fa-regular fa-trash-can"></i>
                </button>
            </div>
            <div class="gallery-info" title="${img.filename}">
                ${img.filename}
            </div>
        `;
        
        // Hook up delete event listener
        card.querySelector('.delete-btn').addEventListener('click', (e) => deleteGalleryImage(img.filename, e));
        
        galleryGrid.appendChild(card);
    });
}

function renderResults(results) {
    resultsGrid.innerHTML = '';
    
    if (results.length === 0) {
        resultsGrid.innerHTML = `
            <div class="placeholder-card">
                <div class="placeholder-icon"><i class="fa-solid fa-triangle-exclamation"></i></div>
                <p>No matches found.</p>
            </div>
        `;
        resultsCount.textContent = "Search complete. Found 0 matching images.";
        return;
    }
    
    resultsCount.textContent = `Search complete. Showing top ${results.length} semantic matches:`;
    
    results.forEach(res => {
        const card = document.createElement('div');
        card.className = 'result-card';
        
        // Define score color category
        let scoreClass = 'score-low';
        if (res.score >= 85) scoreClass = 'score-high';
        else if (res.score >= 65) scoreClass = 'score-medium';
        
        card.innerHTML = `
            <div class="result-image-wrapper">
                <img src="${res.url}" alt="${res.filename}">
                <div class="score-badge ${scoreClass}">${res.score}% Match</div>
            </div>
            <div class="result-info">
                <div class="result-filename" title="${res.filename}">${res.filename}</div>
                <div class="result-actions">
                    <button class="btn btn-accent w-full search-relative-btn">
                        <i class="fa-solid fa-arrows-spin"></i> Search Relative
                    </button>
                </div>
            </div>
        `;
        
        // Search relative functionality
        card.querySelector('.search-relative-btn').addEventListener('click', () => {
            searchWithGalleryImage(res.filename);
        });
        
        resultsGrid.appendChild(card);
    });
}

// ----------------------------------------------------
// Event Listeners
// ----------------------------------------------------

// Dropzone Drag and Drop
['dragenter', 'dragover'].forEach(eventName => {
    searchDropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        searchDropzone.classList.add('dragover');
    }, false);
});

['dragleave', 'drop'].forEach(eventName => {
    searchDropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        searchDropzone.classList.remove('dragover');
    }, false);
});

searchDropzone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length > 0 && files[0].type.startsWith('image/')) {
        const file = files[0];
        showQueryPreview(URL.createObjectURL(file));
        performSearch(file);
    }
});

// Dropzone click trigger
searchDropzone.addEventListener('click', (e) => {
    // Avoid double trigger when clicking preview controls
    if (e.target.closest('#clear-search-btn') || e.target.closest('.preview-overlay')) return;
    searchFileInput.click();
});

searchFileInput.addEventListener('change', (e) => {
    if (searchFileInput.files.length > 0) {
        const file = searchFileInput.files[0];
        showQueryPreview(URL.createObjectURL(file));
        performSearch(file);
    }
});

clearSearchBtn.addEventListener('click', resetQueryPreview);

// Gallery Upload Event Handlers
galleryUploadBtn.addEventListener('click', () => galleryFileInput.click());
galleryFileInput.addEventListener('change', (e) => {
    if (galleryFileInput.files.length > 0) {
        uploadToGallery(galleryFileInput.files);
        galleryFileInput.value = ''; // Reset input
    }
});

// ----------------------------------------------------
// Webcam Operations
// ----------------------------------------------------
webcamToggleBtn.addEventListener('click', async () => {
    try {
        webcamStream = await navigator.mediaDevices.getUserMedia({ 
            video: { facingMode: 'user' } 
        });
        webcamVideo.srcObject = webcamStream;
        webcamContainer.classList.remove('hidden');
        webcamToggleBtn.classList.add('hidden');
    } catch (error) {
        console.error('Webcam access failed:', error);
        showToast('Could not access webcam. Please check permissions.');
    }
});

function stopWebcam() {
    if (webcamStream) {
        webcamStream.getTracks().forEach(track => track.stop());
        webcamStream = null;
    }
    webcamVideo.srcObject = null;
    webcamContainer.classList.add('hidden');
    webcamToggleBtn.classList.remove('hidden');
}

webcamCloseBtn.addEventListener('click', stopWebcam);

webcamCaptureBtn.addEventListener('click', () => {
    if (!webcamStream) return;
    
    // Set canvas dimensions to match video stream aspect ratio
    webcamCanvas.width = webcamVideo.videoWidth;
    webcamCanvas.height = webcamVideo.videoHeight;
    
    const context = webcamCanvas.getContext('2d');
    context.drawImage(webcamVideo, 0, 0, webcamCanvas.width, webcamCanvas.height);
    
    // Convert canvas to blob file
    webcamCanvas.toBlob((blob) => {
        if (blob) {
            const file = new File([blob], 'webcam_capture.jpg', { type: 'image/jpeg' });
            
            // Show preview URL locally
            const previewUrl = URL.createObjectURL(blob);
            showQueryPreview(previewUrl);
            
            // Perform lookup
            performSearch(file);
            stopWebcam();
        }
    }, 'image/jpeg', 0.95);
});

// ----------------------------------------------------
// Page Startup
// ----------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
    loadGallery();
});
