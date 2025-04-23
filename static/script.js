document.addEventListener('DOMContentLoaded', function () {
    // Tab switching functionality
    const tabs = document.querySelectorAll('nav a');
    const sections = document.querySelectorAll('.tool-section');

    tabs.forEach(tab => {
        tab.addEventListener('click', function (e) {
            e.preventDefault();

            // Remove active class from all tabs and sections
            tabs.forEach(t => t.classList.remove('active'));
            sections.forEach(s => s.classList.remove('active'));

            // Add active class to clicked tab and corresponding section
            this.classList.add('active');
            const targetId = this.getAttribute('data-target');
            document.getElementById(targetId).classList.add('active');
        });
    });

    // Audio Extractor Functionality
    setupFileUpload('extractor-file-input', 'extractor-dropzone', 'extractor-file-info', 'extractor-filename', 'extractor-filesize', 'extractor-remove-file');

    // Handle extractor submit
    const extractorSubmitBtn = document.getElementById('extractor-submit');
    extractorSubmitBtn.addEventListener('click', function () {
        const fileInput = document.getElementById('extractor-file-input');
        if (fileInput.files.length === 0) return;

        const file = fileInput.files[0];
        const formData = new FormData();
        formData.append('video', file);

        // Show loader
        document.getElementById('extractor-upload').style.display = 'none';
        document.getElementById('extractor-loader').style.display = 'block';

        fetch('/extract', {
            method: 'POST',
            body: formData
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Hide loader and show result
                    document.getElementById('extractor-loader').style.display = 'none';
                    document.getElementById('extractor-result').style.display = 'block';

                    // Setup download button
                    const downloadBtn = document.getElementById('extractor-download');
                    downloadBtn.addEventListener('click', function () {
                        window.location.href = `/download/${data.session_id}`;
                    });
                } else {
                    alert(`Error: ${data.message}`);
                    document.getElementById('extractor-loader').style.display = 'none';
                    document.getElementById('extractor-upload').style.display = 'block';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred. Please try again.');
                document.getElementById('extractor-loader').style.display = 'none';
                document.getElementById('extractor-upload').style.display = 'block';
            });
    });

    // Reset extractor
    document.getElementById('extractor-reset').addEventListener('click', function () {
        document.getElementById('extractor-result').style.display = 'none';
        document.getElementById('extractor-upload').style.display = 'block';
        document.getElementById('extractor-file-input').value = '';
        document.getElementById('extractor-file-info').style.display = 'none';
    });

    // Audio Replacer Functionality
    setupFileUpload('video-file-input', 'video-dropzone', 'video-file-info', 'video-filename', 'video-filesize', 'video-remove-file');
    setupFileUpload('audio-file-input', 'audio-dropzone', 'audio-file-info', 'audio-filename', 'audio-filesize', 'audio-remove-file');

    // Session ID for the replacer
    let replacerSessionId = null;

    // Handle video submit (step 1)
    const videoSubmitBtn = document.getElementById('video-submit');
    videoSubmitBtn.addEventListener('click', function () {
        const fileInput = document.getElementById('video-file-input');
        if (fileInput.files.length === 0) return;

        const file = fileInput.files[0];
        const formData = new FormData();
        formData.append('video', file);

        // Show loader
        document.getElementById('step-1').style.display = 'none';
        document.getElementById('replacer-loader').style.display = 'block';

        fetch('/upload_video', {
            method: 'POST',
            body: formData
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Hide loader and show step 2
                    document.getElementById('replacer-loader').style.display = 'none';
                    document.getElementById('step-2').style.display = 'block';

                    // Update stepper
                    updateStepper(2);

                    // Store session ID
                    replacerSessionId = data.session_id;
                } else {
                    alert(`Error: ${data.message}`);
                    document.getElementById('replacer-loader').style.display = 'none';
                    document.getElementById('step-1').style.display = 'block';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred. Please try again.');
                document.getElementById('replacer-loader').style.display = 'none';
                document.getElementById('step-1').style.display = 'block';
            });
    });

    // Handle audio submit (step 2)
    const audioSubmitBtn = document.getElementById('audio-submit');
    audioSubmitBtn.addEventListener('click', function () {
        if (!replacerSessionId) {
            alert('Session error. Please start over.');
            return;
        }

        const fileInput = document.getElementById('audio-file-input');
        if (fileInput.files.length === 0) return;

        const file = fileInput.files[0];
        const formData = new FormData();
        formData.append('audio', file);

        // Show loader
        document.getElementById('step-2').style.display = 'none';
        document.getElementById('replacer-loader').style.display = 'block';

        fetch(`/upload_audio/${replacerSessionId}`, {
            method: 'POST',
            body: formData
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Hide loader
                    document.getElementById('replacer-loader').style.display = 'none';

                    // Update stepper and show step 3
                    updateStepper(3);
                    document.getElementById('step-3').style.display = 'block';

                    // Update video source
                    const previewVideo = document.getElementById('preview-video');
                    previewVideo.src = `/static/processed/${data.output_filename}`;
                    previewVideo.load();

                    // Setup download button
                    const downloadBtn = document.getElementById('video-download');
                    downloadBtn.addEventListener('click', function () {
                        window.location.href = `/download/${replacerSessionId}`;
                    });
                } else {
                    alert(`Error: ${data.message}`);
                    document.getElementById('replacer-loader').style.display = 'none';
                    document.getElementById('step-2').style.display = 'block';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred. Please try again.');
                document.getElementById('replacer-loader').style.display = 'none';
                document.getElementById('step-2').style.display = 'block';
            });
    });

    // Reset replacer
    document.getElementById('video-reset').addEventListener('click', function () {
        resetReplacer();
    });

    // Helper Functions
    function setupFileUpload(inputId, dropzoneId, infoId, filenameId, filesizeId, removeId) {
        const fileInput = document.getElementById(inputId);
        const dropzone = document.getElementById(dropzoneId);
        const fileInfo = document.getElementById(infoId);
        const filenameElement = document.getElementById(filenameId);
        const filesizeElement = document.getElementById(filesizeId);
        const removeBtn = document.getElementById(removeId);

        // Handle file input change
        fileInput.addEventListener('change', function () {
            if (this.files.length > 0) {
                const file = this.files[0];
                displayFileInfo(file, fileInfo, filenameElement, filesizeElement);
            }
        });

        // Handle drag & drop
        dropzone.addEventListener('dragover', function (e) {
            e.preventDefault();
            this.classList.add('dragover');
        });

        dropzone.addEventListener('dragleave', function () {
            this.classList.remove('dragover');
        });

        dropzone.addEventListener('drop', function (e) {
            e.preventDefault();
            this.classList.remove('dragover');

            if (e.dataTransfer.files.length > 0) {
                fileInput.files = e.dataTransfer.files;
                const file = e.dataTransfer.files[0];
                displayFileInfo(file, fileInfo, filenameElement, filesizeElement);
            }
        });

        // Handle remove button
        removeBtn.addEventListener('click', function () {
            fileInput.value = '';
            fileInfo.style.display = 'none';
        });
    }

    function displayFileInfo(file, infoElement, nameElement, sizeElement) {
        nameElement.textContent = file.name;
        sizeElement.textContent = formatFileSize(file.size);
        infoElement.style.display = 'block';
    }

    function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' bytes';
        else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
        else return (bytes / 1048576).toFixed(1) + ' MB';
    }

    function updateStepper(step) {
        const steps = document.querySelectorAll('.step');
        steps.forEach(s => s.classList.remove('active'));
        for (let i = 0; i < step; i++) {
            steps[i].classList.add('active');
        }
    }

    function resetReplacer() {
        // Reset file inputs
        document.getElementById('video-file-input').value = '';
        document.getElementById('audio-file-input').value = '';

        // Hide file info
        document.getElementById('video-file-info').style.display = 'none';
        document.getElementById('audio-file-info').style.display = 'none';

        // Hide all steps except step 1
        document.getElementById('step-1').style.display = 'block';
        document.getElementById('step-2').style.display = 'none';
        document.getElementById('step-3').style.display = 'none';

        // Reset stepper
        updateStepper(1);

        // Reset session ID
        replacerSessionId = null;
    }
});