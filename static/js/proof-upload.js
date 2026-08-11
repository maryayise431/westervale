// ===== WESTERVALE proof-upload.js — payment proof preview & remove =====

document.addEventListener('DOMContentLoaded', function () {
    var input = document.getElementById('paymentProof');
    var drop = document.getElementById('proofDrop');
    var preview = document.getElementById('proofPreview');
    var remove = document.getElementById('proofRemove');
    if (!input || !drop || !preview) return;

    function showPreview(file) {
        if (!file) return;
        if (!file.type.startsWith('image/')) {
            showToast('Please select an image file.', 'error', 'Invalid file');
            input.value = '';
            return;
        }
        if (file.size > 5 * 1024 * 1024) {
            showToast('File exceeds the 5MB limit.', 'error', 'File too large');
            input.value = '';
            return;
        }
        var reader = new FileReader();
        reader.onload = function (e) {
            preview.querySelector('img').src = e.target.result;
            preview.style.display = 'block';
            drop.style.display = 'none';
        };
        reader.readAsDataURL(file);
    }

    function resetField() {
        input.value = '';
        preview.querySelector('img').src = '';
        preview.style.display = 'none';
        drop.style.display = '';
    }

    input.addEventListener('change', function () { showPreview(input.files[0]); });

    ['dragenter', 'dragover'].forEach(function (evt) {
        drop.addEventListener(evt, function (e) { e.preventDefault(); drop.classList.add('dragover'); });
    });
    ['dragleave', 'drop'].forEach(function (evt) {
        drop.addEventListener(evt, function (e) { e.preventDefault(); drop.classList.remove('dragover'); });
    });
    drop.addEventListener('drop', function (e) {
        var file = e.dataTransfer.files[0];
        if (file) {
            input.files = e.dataTransfer.files;
            showPreview(file);
        }
    });
    if (remove) remove.addEventListener('click', resetField);
});
